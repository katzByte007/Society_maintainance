import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
from calendar import monthrange

# Conditional Plotly import with fallback
try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    px = None
    go = None

# Constants
LATE_FEE = 1000
FIRST_DUE_DATE = 10
FINAL_DUE_DATE = 28

# File paths
EXCEL_FILE = 'maintenance_data.xlsx'

def init_session_state():
    """Initialize session state variables"""
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
    # Define required columns
    required_columns = {
        'House': list(range(1, 41)),
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

    try:
        if os.path.exists(EXCEL_FILE):
            df = pd.read_excel(EXCEL_FILE)
            
            # Ensure all required columns exist
            for col, default_values in required_columns.items():
                if col not in df.columns:
                    df[col] = default_values
        else:
            # Create a new DataFrame with required columns
            df = pd.DataFrame(required_columns)
    except Exception as e:
        # If there's any issue reading the file, create a new DataFrame
        st.warning(f"Error reading Excel file: {e}. Creating new data.")
        df = pd.DataFrame(required_columns)
    
    return df

def save_data(df):
    """Save data to Excel file"""
    try:
        df.to_excel(EXCEL_FILE, index=False)
    except Exception as e:
        st.error(f"Error saving data: {e}")

class PaymentTracker:
    @staticmethod
    def check_late_payments():
        """Check for late payments and apply late fees"""
        today = datetime.now()
        current_month = today.replace(day=1)
        
        for index, resident in st.session_state.residents.iterrows():
            last_payment_date = resident['Last Payment Date']
            if isinstance(last_payment_date, str):
                try:
                    last_payment_date = datetime.strptime(last_payment_date, '%Y-%m-%d')
                except:
                    last_payment_date = None
            
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
                    st.session_state.residents.loc[index, 'Payment Status'] = 'Late'

    @staticmethod
    def calculate_dues(house_number):
        """Calculate total dues for a specific house"""
        resident = st.session_state.residents[st.session_state.residents['House'] == house_number].iloc[0]
        return resident['Maintenance Amount'] + resident['Extra Charges'] + resident['Late Fees']

class ResidentInterface:
    @staticmethod
    def make_payment():
        st.header("Make Payment")
        
        house_number = st.number_input("Enter Your House Number", min_value=1, max_value=40)
        resident_data = st.session_state.residents[st.session_state.residents['House'] == house_number]
        
        if not resident_data.empty:
            resident = resident_data.iloc[0]
            maintenance_amount = resident['Maintenance Amount']
            extra_charges = resident['Extra Charges']
            late_fees = resident['Late Fees']
            total_amount = maintenance_amount + extra_charges + late_fees
            
            st.write(f"Monthly Maintenance: ₹{maintenance_amount}")
            if extra_charges > 0:
                st.write(f"Extra Charges: ₹{extra_charges}")
            if late_fees > 0:
                st.write(f"Late Fees: ₹{late_fees}")
            st.write(f"Total Amount Due: ₹{total_amount}")
            
            payment_amount = st.number_input("Enter Payment Amount", min_value=0, value=total_amount, step=100)
            
            if st.button("Submit Payment"):
                # Update payment details
                st.session_state.residents.loc[st.session_state.residents['House'] == house_number, 'Paid'] = True
                payment_date = datetime.now().strftime('%Y-%m-%d')
                st.session_state.residents.loc[st.session_state.residents['House'] == house_number, 'Last Payment Date'] = payment_date
                
                # Update payment history
                history = resident['Payment History']
                history.append(f"{payment_date}: ₹{payment_amount}")
                st.session_state.residents.loc[st.session_state.residents['House'] == house_number, 'Payment History'] = [history]
                
                # Reset extra charges and late fees after payment
                st.session_state.residents.loc[st.session_state.residents['House'] == house_number, 'Extra Charges'] = 0
                st.session_state.residents.loc[st.session_state.residents['House'] == house_number, 'Late Fees'] = 0
                st.session_state.residents.loc[st.session_state.residents['House'] == house_number, 'Payment Status'] = 'Paid'
                
                save_data(st.session_state.residents)
                st.success(f"Payment of ₹{payment_amount} recorded for House {house_number}")
        else:
            st.error("Invalid house number")

    @staticmethod
    def view_expenses():
        st.header("View Expenses")
        st.write("Expense Categories and Amounts")
        
        expense_df = pd.DataFrame.from_dict(
            st.session_state.expenditure_categories, 
            orient='index', 
            columns=['Amount']
        )
        expense_df.index.name = 'Category'
        expense_df.reset_index(inplace=True)
        
        st.dataframe(expense_df)
        
        # Visualize expenses if Plotly is available
        if PLOTLY_AVAILABLE and px:
            fig = px.pie(
                expense_df, 
                values='Amount', 
                names='Category', 
                title='Monthly Expense Breakdown'
            )
            st.plotly_chart(fig)

    @staticmethod
    def submit_complaint():
        st.header("Submit Complaint")
        
        if 'complaints' not in st.session_state:
            st.session_state.complaints = []
        
        house_number = st.number_input("Your House Number", min_value=1, max_value=40)
        complaint_type = st.selectbox("Complaint Type", [
            "Maintenance", "Security", "Cleanliness", "Noise", "Others"
        ])
        description = st.text_area("Describe your complaint")
        
        if st.button("Submit Complaint"):
            new_complaint = {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'house': house_number,
                'type': complaint_type,
                'description': description,
                'status': 'Open'
            }
            st.session_state.complaints.append(new_complaint)
            st.success("Complaint submitted successfully")

    @staticmethod
    def book_amenity():
        st.header("Book Amenity")
        
        if 'amenities' not in st.session_state:
            st.session_state.amenities = [
                {'name': 'Gym', 'status': 'Available'},
                {'name': 'Swimming Pool', 'status': 'Available'},
                {'name': 'Community Hall', 'status': 'Available'}
            ]
        
        amenity = st.selectbox("Select Amenity", 
            [amenity['name'] for amenity in st.session_state.amenities 
             if amenity['status'] == 'Available']
        )
        booking_date = st.date_input("Select Booking Date")
        
        if st.button("Book Amenity"):
            # Update amenity status
            for amenity_item in st.session_state.amenities:
                if amenity_item['name'] == amenity:
                    amenity_item['status'] = 'Reserved'
            
            st.success(f"{amenity} booked for {booking_date}")

    @staticmethod
    def view_notices():
        st.header("Notices")
        
        if 'notices' not in st.session_state:
            st.session_state.notices = [
                {
                    'date': datetime.now().strftime('%Y-%m-%d'),
                    'title': 'Monthly Maintenance Reminder',
                    'content': 'Please pay your maintenance dues by the 10th of the month.'
                }
            ]
        
        for notice in st.session_state.notices:
            st.subheader(notice['title'])
            st.write(f"Date: {notice['date']}")
            st.write(notice['content'])
            st.write('---')

def main():
    # Initialize session state first
    init_session_state()
    
    st.title("Smart Apartment Management System")
    
    # Add payment tracking to session state
    if 'payment_tracker' not in st.session_state:
        st.session_state.payment_tracker = PaymentTracker()
    PaymentTracker.check_late_payments()
    
    # User type selection
    user_type = st.radio("Select User Type", ("Admin", "Resident"))

    if user_type == "Admin":
        password = st.text_input("Enter admin password", type="password")
        if password == "admin123":
            st.session_state.user_type = "Admin"
            
            # Admin Navigation
            admin_action = st.sidebar.selectbox(
                "Select Action",
                ["Dashboard", "Manage Residents", "Manage Expenditures"]
            )
            
            if admin_action == "Dashboard":
                st.subheader("Admin Dashboard")
                total_residents = len(st.session_state.residents)
                paid_residents = len(st.session_state.residents[st.session_state.residents['Paid']])
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Total Residents", total_residents)
                col2.metric("Paid Residents", paid_residents)
                col3.metric("Unpaid Residents", total_residents - paid_residents)
                
                # Expenditure Summary
                st.subheader("Monthly Expenditure")
                expense_df = pd.DataFrame.from_dict(
                    st.session_state.expenditure_categories, 
                    orient='index', 
                    columns=['Amount']
                )
                expense_df.index.name = 'Category'
                expense_df.reset_index(inplace=True)
                st.dataframe(expense_df)
                
            elif admin_action == "Manage Residents":
                st.subheader("Resident Management")
                st.dataframe(st.session_state.residents[['House', 'Name', 'Phone', 'Email', 'Payment Status']])
                
            elif admin_action == "Manage Expenditures":
                st.subheader("Manage Expenditures")
                for category, amount in st.session_state.expenditure_categories.items():
                    new_amount = st.number_input(f"{category} Expenditure", value=amount, key=category)
                    st.session_state.expenditure_categories[category] = new_amount
        
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
    # Load residents data
    if 'residents' not in st.session_state:
        st.session_state.residents = load_data()
    
    # Run the main application
    main()
