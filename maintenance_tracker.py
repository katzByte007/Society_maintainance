import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import plotly.express as px
import plotly.graph_objects as go
from calendar import monthrange
import json

# Constants
LATE_FEE = 1000
FIRST_DUE_DATE = 10
FINAL_DUE_DATE = 28

# File paths
EXCEL_FILE = 'maintenance_data.xlsx'
EXPENDITURE_FILE = 'expenditure_data.xlsx'
COMPLAINTS_FILE = 'complaints.xlsx'
AMENITY_FILE = 'amenities.xlsx'
MEETING_FILE = 'meetings.xlsx'
NOTICE_FILE = 'notices.xlsx'

# Initialize session state variables
def init_session_state():
    if 'expenditure_categories' not in st.session_state:
        st.session_state.expenditure_categories = {
            'Watchman': 15000,
            'Cleaning': 12000,
            'Water Tanker': 8000,
            'Electricity (Common Areas)': 5000,
            'Garden Maintenance': 3000,
            'Lift Maintenance': 4000,
            'Security System': 2000,
            'Emergency Fund': 5000,
            'Repairs and Maintenance': 10000
        }

def load_data():
    """Load or create resident data"""
    if os.path.exists(EXCEL_FILE):
        df = pd.read_excel(EXCEL_FILE)
        # Ensure all required columns exist
        required_columns = {
            'House': range(1, 41),
            'Name': ['Resident ' + str(i) for i in range(1, 41)],
            'Phone': ['1234567890' for _ in range(40)],
            'Email': ['resident@example.com' for _ in range(40)],
            'Paid': [False for _ in range(40)],
            'Last Payment Date': [None for _ in range(40)],
            'Last Payment Month': [None for _ in range(40)],
            'Payment History': [[] for _ in range(40)],
            'Maintenance Amount': [2000 for _ in range(40)],
            'Extra Charges': [0 for _ in range(40)],
            'Late Fees': [0 for _ in range(40)],
            'Total Dues': [0 for _ in range(40)],
            'Payment Status': ['Unpaid' for _ in range(40)]
        }
        
        for col, default_values in required_columns.items():
            if col not in df.columns:
                df[col] = default_values
    else:
        df = pd.DataFrame(required_columns)
    return df

def save_data(df):
    """Save data to Excel file"""
    df.to_excel(EXCEL_FILE, index=False)

class PaymentTracker:
    @staticmethod
    def check_late_payments():
        """Check for late payments and apply late fees"""
        today = datetime.now()
        current_month = today.replace(day=1)
        
        for index, resident in st.session_state.residents.iterrows():
            last_payment_date = resident['Last Payment Date']
            if isinstance(last_payment_date, str):
                last_payment_date = datetime.strptime(last_payment_date, '%Y-%m-%d')
            
            if (last_payment_date is None or 
                (isinstance(last_payment_date, datetime) and 
                 last_payment_date.replace(day=1) < current_month)):
                
                if today.day > FIRST_DUE_DATE:
                    st.session_state.residents.loc[index, 'Late Fees'] = LATE_FEE
                    st.session_state.residents.loc[index, 'Total Dues'] = (
                        resident['Maintenance Amount'] + 
                        resident['Extra Charges'] + 
                        LATE_FEE
                    )

    @staticmethod
    def calculate_dues(house_number):
        """Calculate total dues for a specific house"""
        resident = st.session_state.residents[st.session_state.residents['House'] == house_number].iloc[0]
        return resident['Maintenance Amount'] + resident['Extra Charges'] + resident['Late Fees']

class FinancialDashboard:
    @staticmethod
    def display_monthly_summary():
        st.subheader("Monthly Financial Summary")
        
        col1, col2, col3 = st.columns(3)
        
        total_expected = len(st.session_state.residents) * 2000
        total_collected = st.session_state.residents[st.session_state.residents['Paid']]['Maintenance Amount'].sum()
        total_expenses = sum(st.session_state.expenditure_categories.values())
        
        col1.metric("Expected Collection", f"₹{total_expected:,}")
        col2.metric("Actual Collection", f"₹{total_collected:,}")
        col3.metric("Total Expenses", f"₹{total_expenses:,}")
        
        # Create expense breakdown pie chart
        fig = px.pie(
            values=list(st.session_state.expenditure_categories.values()),
            names=list(st.session_state.expenditure_categories.keys()),
            title="Expense Breakdown"
        )
        st.plotly_chart(fig)

class AdminInterface:
    @staticmethod
    def manage_expenditures():
        st.subheader("Manage Monthly Expenditures")
        
        with st.expander("Add New Expenditure Category"):
            new_category = st.text_input("New Category Name")
            new_amount = st.number_input("Default Monthly Amount", min_value=0)
            if st.button("Add Category"):
                st.session_state.expenditure_categories[new_category] = new_amount
                st.success(f"Added {new_category} to expenditure categories")

        st.subheader("Edit Existing Categories")
        for category, amount in st.session_state.expenditure_categories.items():
            col1, col2, col3 = st.columns([2, 1, 1])
            col1.write(category)
            new_amount = col2.number_input(f"Amount for {category}", value=amount, key=f"exp_{category}")
            if col3.button("Update", key=f"update_{category}"):
                st.session_state.expenditure_categories[category] = new_amount
                st.success(f"Updated {category} amount")

    @staticmethod
    def manage_vendors():
        st.subheader("Vendor Management")
        
        if 'vendors' not in st.session_state:
            st.session_state.vendors = []
            
        with st.expander("Add New Vendor"):
            vendor_name = st.text_input("Vendor Name")
            vendor_service = st.text_input("Service Provided")
            vendor_contact = st.text_input("Contact Number")
            vendor_email = st.text_input("Email")
            
            if st.button("Add Vendor"):
                new_vendor = {
                    'name': vendor_name,
                    'service': vendor_service,
                    'contact': vendor_contact,
                    'email': vendor_email
                }
                st.session_state.vendors.append(new_vendor)
                st.success("Vendor added successfully")
        
        if st.session_state.vendors:
            st.write("Current Vendors:")
            vendor_df = pd.DataFrame(st.session_state.vendors)
            st.dataframe(vendor_df)

    @staticmethod
    def manage_complaints():
        st.subheader("Complaint Management")
        
        if 'complaints' not in st.session_state:
            st.session_state.complaints = []
            
        with st.expander("Register New Complaint"):
            house_number = st.number_input("House Number", min_value=1, max_value=40)
            complaint_type = st.selectbox("Complaint Type", [
                "Maintenance", "Security", "Cleanliness", "Noise", "Others"
            ])
            description = st.text_area("Description")
            
            if st.button("Submit Complaint"):
                new_complaint = {
                    'date': datetime.now().strftime('%Y-%m-%d'),
                    'house': house_number,
                    'type': complaint_type,
                    'description': description,
                    'status': 'Open',
                    'resolution': ''
                }
                st.session_state.complaints.append(new_complaint)
                st.success("Complaint registered successfully")
        
        if st.session_state.complaints:
            st.write("Current Complaints:")
            complaints_df = pd.DataFrame(st.session_state.complaints)
            st.dataframe(complaints_df)
            
            # Update complaint status
            with st.expander("Update Complaint Status"):
                complaint_index = st.number_input("Complaint Index", min_value=0, max_value=len(st.session_state.complaints)-1)
                new_status = st.selectbox("New Status", ["Open", "In Progress", "Resolved", "Closed"])
                resolution = st.text_area("Resolution Details")
                
                if st.button("Update Status"):
                    st.session_state.complaints[complaint_index]['status'] = new_status
                    st.session_state.complaints[complaint_index]['resolution'] = resolution
                    st.success("Complaint status updated")

    @staticmethod
    def manage_amenities():
        st.subheader("Amenity Management")
        
        if 'amenities' not in st.session_state:
            st.session_state.amenities = []
            
        with st.expander("Add New Amenity"):
            amenity_name = st.text_input("Amenity Name")
            status = st.selectbox("Status", ["Available", "Under Maintenance", "Reserved"])
            maintenance_frequency = st.number_input("Maintenance Frequency (days)", min_value=1)
            
            if st.button("Add Amenity"):
                new_amenity = {
                    'name': amenity_name,
                    'status': status,
                    'maintenance_frequency': maintenance_frequency,
                    'last_maintenance': datetime.now().strftime('%Y-%m-%d'),
                    'next_maintenance': (datetime.now() + timedelta(days=maintenance_frequency)).strftime('%Y-%m-%d')
                }
                st.session_state.amenities.append(new_amenity)
                st.success("Amenity added successfully")
        
        if st.session_state.amenities:
            st.write("Current Amenities:")
            amenities_df = pd.DataFrame(st.session_state.amenities)
            st.dataframe(amenities_df)

    @staticmethod
    def manage_meetings():
        st.subheader("Meeting Management")
        
        if 'meetings' not in st.session_state:
            st.session_state.meetings = []
            
        with st.expander("Schedule New Meeting"):
            meeting_date = st.date_input("Meeting Date")
            meeting_type = st.selectbox("Meeting Type", ["General Body", "Committee", "Emergency"])
            agenda = st.text_area("Meeting Agenda")
            expected_attendees = st.multiselect("Expected Attendees", [f"House {i}" for i in range(1, 41)])
            
            if st.button("Schedule Meeting"):
                new_meeting = {
                    'date': meeting_date.strftime('%Y-%m-%d'),
                    'type': meeting_type,
                    'agenda': agenda,
                    'attendees': expected_attendees,
                    'minutes': '',
                    'status': 'Scheduled'
                }
                st.session_state.meetings.append(new_meeting)
                st.success("Meeting scheduled successfully")
        
        if st.session_state.meetings:
            st.write("Upcoming Meetings:")
            meetings_df = pd.DataFrame(st.session_state.meetings)
            st.dataframe(meetings_df)

    @staticmethod
    def payment_tracking_dashboard():
        st.subheader("Payment Tracking Dashboard")
        
        # Date selection for historical view
        selected_month = st.date_input(
            "Select Month to View",
            datetime.now().replace(day=1)
        ).replace(day=1)
        
        tab1, tab2, tab3, tab4 = st.tabs([
            "Current Month Status", 
            "Late Payments", 
            "Historical Dues",
            "Detailed Payment History"
        ])
        
        with tab1:
            st.subheader("Current Month Payment Status")
            
            # Calculate payment statistics
            total_residents = len(st.session_state.residents)
            paid_residents = len(st.session_state.residents[st.session_state.residents['Paid']])
            unpaid_residents = total_residents - paid_residents
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Residents", total_residents)
            col2.metric("Paid", paid_residents)
            col3.metric("Unpaid", unpaid_residents)
            
            # Display detailed lists
            st.write("Payment Details:")
            st.dataframe(st.session_state.residents[['House', 'Name', 'Payment Status', 'Total Dues']])
            
        with tab2:
            st.subheader("Late Payments")
            late_payers = st.session_state.residents[st.session_state.residents['Late Fees'] > 0]
            if not late_payers.empty:
                st.dataframe(late_payers[['House', 'Name', 'Late Fees', 'Total Dues']])
            else:
                st.write("No late payments for the current month")
            
        with tab3:
            st.subheader("Historical Payment Analysis")
            
            # Create sample historical data
            dates = pd.date_range(start='2024-01-01', end=datetime.now(), freq='M')
            historical_data = []
            
            for date in dates:
                historical_data.append({
                    'Month': date.strftime('%Y-%m'),
                    'Expected': total_residents * 2000,
                    'Collected': int((total_residents * 2000) * 0.8)  # Sample data: 80% collection
                })
            
            hist_df = pd.DataFrame(historical_data)
            fig = px.line(hist_df, x='Month', y=['Expected', 'Collected'],
                         title='Monthly Payment Collection Trend')
            st.plotly_chart(fig)
            
        with tab4:
            st.subheader("Payment History by House")
            house_number = st.number_input("Enter House Number", min_value=1, max_value=40)
            
            if st.button("View History"):
                resident = st.session_state.residents[st.session_state.residents['House'] == house_number].iloc[0]
                st.write(f"Payment History for House {house_number} - {resident['Name']}")
                
                if resident['Payment History']:
                    history_df = pd.DataFrame(resident['Payment History'])
                    st.dataframe(history_df)
                else:
                    st.write("No payment history available")
    @staticmethod
    def generate_monthly_report():
        st.subheader("Monthly Payment Report")
        report_month = st.date_input("Select Month", datetime.now().replace(day=1))
        
        if st.button("Generate Report"):
            # Create report DataFrame
            report_data = []
            for _, resident in st.session_state.residents.iterrows():
                payment_status = "Unpaid"
                payment_date = None
                payment_amount = 0
                late_fee = 0
                
                # Check payment history for the selected month
                for payment in resident['Payment History']:
                    date = datetime.strptime(payment.split(': ₹')[0], '%Y-%m-%d')
                    if date.month == report_month.month and date.year == report_month.year:
                        payment_status = "Paid"
                        payment_date = date
                        payment_amount = float(payment.split(': ₹')[1])
                        if date.day > FIRST_DUE_DATE:
                            late_fee = LATE_FEE
                
                report_data.append({
                    'House': resident['House'],
                    'Name': resident['Name'],
                    'Status': payment_status,
                    'Payment Date': payment_date,
                    'Amount Paid': payment_amount,
                    'Late Fee': late_fee,
                    'Total Amount': payment_amount + late_fee
                })
            
            report_df = pd.DataFrame(report_data)
            st.dataframe(report_df)
            
            # Summary statistics
            st.subheader("Summary")
            total_collected = report_df['Total Amount'].sum()
            total_late_fees = report_df['Late Fee'].sum()
            total_expected = len(st.session_state.residents) * 2000
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Collected", f"₹{total_collected:,.2f}")
            col2.metric("Late Fees Collected", f"₹{total_late_fees:,.2f}")
            col3.metric("Expected Amount", f"₹{total_expected:,.2f}")
            col4.metric("Collection Rate", f"{(total_collected/total_expected)*100:.1f}%")

class ResidentInterface:
    @staticmethod
    def make_payment():
        st.header("Make Payment")
        
        house_number = st.number_input("Enter Your House Number", min_value=1, max_value=40)
        resident_data = st.session_state.residents[st.session_state.residents['House'] == house_number]
        
        if not resident_data.empty:
            maintenance_amount = resident_data['Maintenance Amount'].iloc[0]
            extra_charges = resident_data['Extra Charges'].iloc[0]
            total_amount = maintenance_amount + extra_charges
            
            st.write(f"Monthly Maintenance: ₹{maintenance_amount}")
            if extra_charges > 0:
                st.write(f"Extra Charges: ₹{extra_charges}")
            st.write(f"Total Amount Due: ₹{total_amount}")
            
            payment_amount = st.number_input("Enter Payment Amount", min_value=0, value=total_amount, step=100)
            
            if st.button("Submit Payment"):
                st.session_state.residents.loc[st.session_state.residents['House'] == house_number, 'Paid'] = True
                payment_date = datetime.now().strftime('%Y-%m-%d')
                st.session_state.residents.loc[st.session_state.residents['House'] == house_number, 'Last Payment Date'] = payment_date
                
                # Update payment history
                history = st.session_state.residents.loc[st.session_state.residents['House'] == house_number, 'Payment History'].iloc[0]
                history.append(f"{payment_date}: ₹{payment_amount}")
                st.session_state.residents.loc[st.session_state.residents['House'] == house_number, 'Payment History'] = [history]
                
                # Reset extra charges after payment
                st.session_state.residents.loc[st.session_state.residents['House'] == house_number, 'Extra Charges'] = 0
                
                save_data(st.session_state.residents)
                st.success(f"Payment of ₹{payment_amount} recorded for House {house_number}")
        else:
            st.error("Invalid house number")

    

def main():
    # Initialize session state first
    init_session_state()
    
    st.title("Smart Apartment Management System")
    
    # Add payment tracking to session state
    if 'payment_tracker' not in st.session_state:
        st.session_state.payment_tracker = PaymentTracker()
    PaymentTracker.check_late_payments()
    
    # type selection
    user_type = st.radio("Select User Type", ("Admin", "Resident"))

    if user_type == "Admin":
        password = st.text_input("Enter admin password", type="password")
        if password == "admin123":
            st.session_state.user_type = "Admin"
            
            # Admin Navigation
            admin_action = st.sidebar.selectbox(
                "Select Action",
                ["Dashboard","Payment Tracking", "Manage Expenditures", "Manage Vendors", 
                 "Manage Complaints", "Manage Amenities", "Manage Meetings",
                 "Generate Reports","Monthly Payment Report"]
            )
            
            if admin_action == "Dashboard":
                FinancialDashboard.display_monthly_summary()
            elif admin_action == "Manage Expenditures":
                AdminInterface.manage_expenditures()
            elif admin_action == "Manage Vendors":
                AdminInterface.manage_vendors()
            elif admin_action == "Manage Complaints":
                AdminInterface.manage_complaints()
            elif admin_action == "Manage Amenities":
                AdminInterface.manage_amenities()
            elif admin_action == "Manage Meetings":
                AdminInterface.manage_meetings()
            elif admin_action == "Generate Reports":
                AdminInterface.generate_reports()
            elif admin_action == "Payment Tracking":
                AdminInterface.payment_tracking_dashboard()
            elif admin_action == "Monthly Payment Report":
                AdminInterface.generate_monthly_report()
                
        elif password:
            st.error("Incorrect password")
            
    elif user_type == "Resident":
        st.session_state.user_type = "Resident"
        
        # Resident Navigation
        resident_action = st.sidebar.selectbox(
            "Select Action",
            ["Make Payment", "View Expenses", "Submit Complaint",
             "Book Amenity", "View Notices"]
        )
        
        if resident_action == "Make Payment":
            ResidentInterface.make_payment()
        elif resident_action == "View Expenses":
            ResidentInterface.view_expenses()
        elif resident_action == "Submit Complaint":
            ResidentInterface.submit_complaint()
        elif resident_action == "Book Amenity":
            ResidentInterface.book_amenity()
        elif resident_action == "View Notices":
            ResidentInterface.view_notices()

if __name__ == "__main__":
    if 'residents' not in st.session_state:
        st.session_state.residents = load_data()
    main()