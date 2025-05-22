
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.title("🏢 Dashboard Monitoring Pendanaan Multi-Perusahaan & Multi-Bank")

if "companies" not in st.session_state:
    st.session_state.companies = {}

today = datetime.today().date()
st.markdown(f"🗓️ **Hari Ini:** {today.strftime('%d %B %Y')}")

# Sidebar input
st.sidebar.header("➕ Tambah Data Pinjaman")
company_name = st.sidebar.text_input("Nama Perusahaan")
bank_name = st.sidebar.text_input("Nama Bank")
principal = st.sidebar.number_input("Jumlah Plafon Pinjaman (Rp)", step=1_000_000)

split_option = st.sidebar.checkbox("Pisahkan Plafon Berdasarkan Jenis Pendanaan?")
split_details = {}
interest_details = {}
jenis_non_split = ""
interest_non_split = 0.0

if split_option:
    split_count = st.sidebar.number_input("Jumlah Jenis Pendanaan", min_value=1, max_value=10, value=2, step=1)
    for i in range(split_count):
        jenis = st.sidebar.text_input(f"Jenis Pendanaan #{i+1}", key=f"jenis_{i}")
        nilai = st.sidebar.number_input(f"Nilai Pendanaan {jenis}", key=f"nilai_{i}", step=1_000_000, value=0)
        suku_bunga = st.sidebar.number_input(f"Tingkat Bunga Tahunan untuk {jenis} (%)", key=f"bunga_{i}", value=8.0, step=0.1)
        if jenis:
            split_details[jenis] = nilai
            interest_details[jenis] = suku_bunga
    total_split = sum(split_details.values())
    if total_split > principal:
        st.sidebar.error("Total nilai jenis pendanaan melebihi plafon utama!")
else:
    jenis_non_split = st.sidebar.text_input("Jenis Pendanaan", placeholder="Contoh: Kredit Modal Kerja")
    interest_non_split = st.sidebar.number_input("Tingkat Bunga Tahunan (%)", value=8.0, step=0.1)

tenor = st.sidebar.number_input("Total Tenor (bulan)", value=108, step=1)
principal_interval = st.sidebar.selectbox("Frekuensi Pembayaran Pokok (bulan)", [1, 3, 6])
principal_portion = st.sidebar.number_input("Porsi Pembayaran Pokok per Termin (Rp)", value=10_000_000, step=1_000_000)
interest_interval = st.sidebar.selectbox("Frekuensi Pembayaran Bunga (bulan)", [1, 3, 6])
start_date = st.sidebar.date_input("Tanggal Mulai Pinjaman", datetime.today())
principal_start_date = st.sidebar.date_input("Tanggal Mulai Pembayaran Pokok (Opsional)", value=None)
due_day = st.sidebar.number_input("Tanggal Jatuh Tempo Pembayaran (1-31)", min_value=1, max_value=31, value=25)

if st.sidebar.button("Tambah Pinjaman") and company_name and bank_name and principal > 0:
    schedule = []
    remaining_principal = principal
    annual_rate_map = {k: v / 100 for k, v in interest_details.items()}
    annual_rate_default = interest_non_split / 100
    use_principal_start = isinstance(principal_start_date, datetime)
    last_due_date = datetime.combine(start_date, datetime.min.time())

    for month in range(1, tenor + 1):
        row = {"Bulan Ke-": month}
        current_month = (start_date.month - 1 + month) % 12 + 1
        current_year = start_date.year + ((start_date.month - 1 + month) // 12)

        try:
            due_date = datetime(current_year, current_month, due_day)
        except ValueError:
            last_day = (datetime(current_year, current_month + 1, 1) - timedelta(days=1)).day if current_month < 12 else 31
            due_date = datetime(current_year, current_month, last_day)

        row["Jatuh Tempo"] = due_date.strftime("%Y-%m-%d")

        # Pembayaran pokok hanya jika sudah lewat tanggal mulai pokok
        principal_payment = 0
        if month % principal_interval == 0 and remaining_principal > 0:
    if use_principal_start:
        if due_date.date() < principal_start_date:
            principal_payment = 0  # Lewati jika belum masuk tanggal dimulainya pokok
        else:
            principal_payment = min(principal_portion, remaining_principal)
    else:
        principal_payment = min(principal_portion, remaining_principal)
else:
    principal_payment = 0
        remaining_principal -= principal_payment

        # Bunga berbasis harian
        total_interest = 0
        bunga_rincian = {}
        if remaining_principal > 0 and month % interest_interval == 0:
            days_diff = (due_date - last_due_date).days
            if split_option:
                for jenis, nilai in split_details.items():
                    bunga = round(nilai * annual_rate_map[jenis] / 365 * days_diff)
                    bunga_rincian[jenis] = bunga
                    total_interest += bunga
            else:
                bunga = round(remaining_principal * annual_rate_default / 365 * days_diff)
                total_interest = bunga
        last_due_date = due_date

        row["Pokok"] = principal_payment
        row["Bunga"] = total_interest
        if split_option:
            for jenis, nilai in bunga_rincian.items():
                row[f"Bunga ({jenis})"] = nilai
        row["Total Pembayaran"] = principal_payment + total_interest
        row["Sisa Pinjaman"] = max(remaining_principal, 0)
        row["Status"] = "Lunas" if row["Sisa Pinjaman"] <= 0 and due_date.date() <= today else "-"
        schedule.append(row)

        if remaining_principal <= 0 and total_interest == 0:
            break

    df_schedule = pd.DataFrame(schedule)

    real_time_status = "✅ LUNAS" if df_schedule[df_schedule['Jatuh Tempo'] <= today.strftime('%Y-%m-%d')]['Sisa Pinjaman'].iloc[-1] <= 0 else "❌ BELUM LUNAS"

    if company_name not in st.session_state.companies:
        st.session_state.companies[company_name] = {}

    st.session_state.companies[company_name][bank_name] = {
        "principal": principal,
        "rate": interest_details if split_option else interest_non_split,
        "tenor": tenor,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "principal_start_date": principal_start_date.strftime("%Y-%m-%d") if use_principal_start else None,
        "due_day": due_day,
        "split": split_option,
        "split_details": split_details,
        "jenis_non_split": jenis_non_split,
        "schedule": df_schedule,
        "lunas": real_time_status
    }

    st.success(f"✅ Pinjaman dari {bank_name} untuk perusahaan {company_name} berhasil ditambahkan.")

# Ringkasan
st.header("🏢 Pilih Perusahaan untuk Melihat Pinjaman")
if st.session_state.companies:
    selected_company = st.selectbox("Perusahaan", list(st.session_state.companies.keys()))
    if selected_company:
        banks_data = st.session_state.companies[selected_company]
        if banks_data:
            st.subheader(f"📋 Ringkasan Pinjaman - {selected_company}")
            summary_data = []
            for bank, data in banks_data.items():
                df = data["schedule"]
                last_paid = df[df["Jatuh Tempo"] <= today.strftime('%Y-%m-%d')]
                outstanding = last_paid["Sisa Pinjaman"].iloc[-1] if not last_paid.empty else data["principal"]
                status = data["lunas"]
                if data.get("split"):
                    plafon_info = "; ".join([
                        f"{jenis}: Rp{nilai:,} @ {interest_details[jenis]:.2f}%" for jenis, nilai in data["split_details"].items()
                    ])
                else:
                    plafon_info = f"{data['jenis_non_split']} @ {data['rate']:.2f}%" if data['jenis_non_split'] else "-"
                summary_data.append({
                    "Bank": bank,
                    "Jumlah Plafon": f"Rp{data['principal']:,}",
                    "Suku Bunga": plafon_info,
                    "Tenor (bulan)": data["tenor"],
                    "Tanggal Mulai": data["start_date"],
                    "Tanggal Mulai Pokok": data["principal_start_date"] or "-",
                    "Tanggal Jatuh Tempo": f"Tgl {data['due_day']}",
                    "Outstanding Saat Ini": f"Rp{outstanding:,}",
                    "Status Real-time": status
                })
            df_summary = pd.DataFrame(summary_data)
            st.dataframe(df_summary, use_container_width=True)

            st.subheader("📅 Jadwal Pembayaran")
            selected_bank = st.selectbox("Pilih Bank", list(banks_data.keys()))
            st.dataframe(banks_data[selected_bank]["schedule"], use_container_width=True)
        else:
            st.info("Perusahaan ini belum memiliki pinjaman.")
else:
    st.info("Belum ada data pinjaman ditambahkan.")
