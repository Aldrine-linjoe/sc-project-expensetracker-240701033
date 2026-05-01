import base64
import hashlib
import hmac
import os
from datetime import date, datetime

import pandas as pd
import streamlit as st


APP_TITLE = "Smart Expense Tracker"
DATA_DIR = "data"
USERS_CSV = os.path.join(DATA_DIR, "users.csv")
EXPENSES_CSV = os.path.join(DATA_DIR, "expenses.csv")

USER_COLUMNS = ["id", "username", "email", "password_hash", "salt", "created_at"]
EXPENSE_COLUMNS = [
    "id",
    "user_id",
    "amount",
    "category",
    "description",
    "expense_date",
    "created_at",
]

EXPENSE_CATEGORIES = [
    "Food",
    "Transport",
    "Shopping",
    "Bills",
    "Education",
    "Health",
    "Entertainment",
    "Other",
]


def initialize_csv_files():
    os.makedirs(DATA_DIR, exist_ok=True)

    if not os.path.exists(USERS_CSV):
        pd.DataFrame(columns=USER_COLUMNS).to_csv(USERS_CSV, index=False)

    if not os.path.exists(EXPENSES_CSV):
        pd.DataFrame(columns=EXPENSE_COLUMNS).to_csv(EXPENSES_CSV, index=False)


def read_users():
    initialize_csv_files()
    return pd.read_csv(USERS_CSV, dtype={"id": "Int64", "email": str})


def write_users(users):
    users.to_csv(USERS_CSV, index=False)


def read_expenses():
    initialize_csv_files()
    expenses = pd.read_csv(EXPENSES_CSV, dtype={"id": "Int64", "user_id": "Int64"})
    if not expenses.empty:
        expenses["amount"] = pd.to_numeric(expenses["amount"], errors="coerce").fillna(0)
    return expenses


def write_expenses(expenses):
    expenses.to_csv(EXPENSES_CSV, index=False)


def next_id(dataframe):
    if dataframe.empty:
        return 1
    return int(pd.to_numeric(dataframe["id"], errors="coerce").max()) + 1


def hash_password(password, salt=None):
    if salt is None:
        salt = os.urandom(16)
    elif isinstance(salt, str):
        salt = base64.b64decode(salt.encode("utf-8"))

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        120_000,
    )
    return (
        base64.b64encode(password_hash).decode("utf-8"),
        base64.b64encode(salt).decode("utf-8"),
    )


def register_user(username, email, password):
    users = read_users()
    cleaned_email = email.strip().lower()

    if not users.empty and cleaned_email in users["email"].str.lower().values:
        return False, "An account with this email already exists."

    password_hash, salt = hash_password(password)
    new_user = {
        "id": next_id(users),
        "username": username.strip(),
        "email": cleaned_email,
        "password_hash": password_hash,
        "salt": salt,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    users = pd.concat([users, pd.DataFrame([new_user])], ignore_index=True)
    write_users(users)
    return True, "Account created successfully. Please login."


def authenticate_user(email, password):
    users = read_users()
    cleaned_email = email.strip().lower()

    if users.empty:
        return None

    matched_users = users[users["email"].str.lower() == cleaned_email]
    if matched_users.empty:
        return None

    user = matched_users.iloc[0]
    entered_hash, _ = hash_password(password, user["salt"])
    if hmac.compare_digest(entered_hash, user["password_hash"]):
        return {
            "id": int(user["id"]),
            "username": user["username"],
            "email": user["email"],
        }
    return None


def add_expense(user_id, amount, category, description, expense_date):
    expenses = read_expenses()
    new_expense = {
        "id": next_id(expenses),
        "user_id": user_id,
        "amount": float(amount),
        "category": category,
        "description": description.strip(),
        "expense_date": expense_date.isoformat(),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    expenses = pd.concat([expenses, pd.DataFrame([new_expense])], ignore_index=True)
    write_expenses(expenses)


def load_expenses(user_id):
    expenses = read_expenses()
    if expenses.empty:
        return pd.DataFrame(columns=["ID", "Date", "Category", "Description", "Amount"])

    user_expenses = expenses[expenses["user_id"].astype(int) == int(user_id)].copy()
    if user_expenses.empty:
        return pd.DataFrame(columns=["ID", "Date", "Category", "Description", "Amount"])

    user_expenses = user_expenses.sort_values(
        by=["expense_date", "id"],
        ascending=[False, False],
    )
    user_expenses = user_expenses.rename(
        columns={
            "id": "ID",
            "expense_date": "Date",
            "category": "Category",
            "description": "Description",
            "amount": "Amount",
        }
    )
    return user_expenses[["ID", "Date", "Category", "Description", "Amount"]]


def setup_session_state():
    st.session_state.setdefault("logged_in", False)
    st.session_state.setdefault("user", None)
    st.session_state.setdefault("page", "Login")


def apply_styles():
    st.markdown(
        """
        <style>
        .main .block-container {
            padding-top: 2rem;
            max-width: 1120px;
        }
        div[data-testid="stMetric"] {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 14px 16px;
            box-shadow: 0 1px 4px rgba(0, 0, 0, 0.18);
        }
        div[data-testid="stMetric"] label,
        div[data-testid="stMetric"] div {
            color: #f2f6fb;
        }
        .section-title {
            font-size: 1.15rem;
            font-weight: 700;
            margin: 1rem 0 0.4rem;
        }
        .app-subtitle {
            color: #526070;
            margin-top: -0.5rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def show_login_page():
    st.title(APP_TITLE)
    st.markdown(
        '<p class="app-subtitle">Login to track expenses and view spending analytics.</p>',
        unsafe_allow_html=True,
    )

    login_tab, register_tab = st.tabs(["Login", "Register"])

    with login_tab:
        st.subheader("User Login")
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")

        if st.button("Login", type="primary", use_container_width=True):
            if not email.strip() or not password:
                st.error("Please enter both email and password.")
                return

            user = authenticate_user(email, password)
            if user:
                st.session_state.logged_in = True
                st.session_state.user = user
                st.session_state.page = "Dashboard"
                st.success("Login successful.")
                st.rerun()
            else:
                st.error("Incorrect email or password.")

    with register_tab:
        st.subheader("User Registration")
        username = st.text_input("Username", key="register_username")
        email = st.text_input("Email", key="register_email")
        password = st.text_input("Password", type="password", key="register_password")

        if st.button("Create Account", use_container_width=True):
            if not username.strip() or not email.strip() or not password:
                st.error("All registration fields are required.")
                return
            if "@" not in email or "." not in email:
                st.error("Please enter a valid email address.")
                return
            if len(password) < 6:
                st.error("Password must contain at least 6 characters.")
                return

            success, message = register_user(username, email, password)
            if success:
                st.success(message)
            else:
                st.error(message)


def show_sidebar():
    user = st.session_state.user
    st.sidebar.title(APP_TITLE)
    st.sidebar.write(f"Logged in as **{user['username']}**")
    st.sidebar.write(user["email"])
    st.sidebar.divider()

    pages = ["Dashboard", "Add Expense", "Analytics"]
    st.session_state.page = st.sidebar.radio(
        "Navigation",
        pages,
        index=pages.index(st.session_state.page) if st.session_state.page in pages else 0,
    )

    st.sidebar.divider()
    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user = None
        st.session_state.page = "Login"
        st.success("Logged out successfully.")
        st.rerun()


def expense_summary(expenses):
    total_expense = expenses["Amount"].sum()
    transaction_count = len(expenses)
    if expenses.empty:
        highest_category = "No data"
    else:
        highest_category = (
            expenses.groupby("Category")["Amount"].sum().sort_values(ascending=False).index[0]
        )
    return total_expense, transaction_count, highest_category


def show_dashboard():
    user = st.session_state.user
    expenses = load_expenses(user["id"])

    st.title("Expense Dashboard")
    st.caption("A clear view of your transactions, totals, and spending pattern.")

    if expenses.empty:
        st.info("No expenses exist yet. Add your first expense from the Add Expense page.")
        return

    total_expense, transaction_count, highest_category = expense_summary(expenses)
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Expenses", f"Rs. {total_expense:,.2f}")
    col2.metric("Transactions", transaction_count)
    col3.metric("Highest Category", highest_category)

    st.markdown('<div class="section-title">All Expenses</div>', unsafe_allow_html=True)
    st.dataframe(expenses, use_container_width=True, hide_index=True)

    st.markdown('<div class="section-title">Recent Transactions</div>', unsafe_allow_html=True)
    st.dataframe(expenses.head(5), use_container_width=True, hide_index=True)


def show_add_expense():
    st.title("Add Expense")
    st.caption("Record a transaction and the dashboard will update immediately.")

    with st.form("expense_form", clear_on_submit=True):
        amount = st.number_input("Expense Amount", min_value=0.0, step=10.0, format="%.2f")
        category = st.selectbox("Category", EXPENSE_CATEGORIES)
        description = st.text_input("Description")
        expense_date = st.date_input("Date", value=date.today())
        submitted = st.form_submit_button("Save Expense", type="primary", use_container_width=True)

    if submitted:
        if amount <= 0:
            st.error("Expense amount must be greater than zero.")
            return
        if not description.strip():
            st.error("Description cannot be empty.")
            return

        add_expense(
            st.session_state.user["id"],
            amount,
            category,
            description,
            expense_date,
        )
        st.success("Expense added successfully.")
        st.session_state.page = "Dashboard"
        st.rerun()


def show_analytics():
    expenses = load_expenses(st.session_state.user["id"])

    st.title("Expense Analytics")
    st.caption("Category-wise analysis and spending summary.")

    if expenses.empty:
        st.info("No expenses exist yet. Analytics will appear after adding expenses.")
        return

    total_expense, transaction_count, highest_category = expense_summary(expenses)
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Expenses", f"Rs. {total_expense:,.2f}")
    col2.metric("Transactions", transaction_count)
    col3.metric("Top Category", highest_category)

    category_totals = (
        expenses.groupby("Category", as_index=False)["Amount"].sum().sort_values("Amount", ascending=False)
    )

    st.markdown('<div class="section-title">Category-wise Totals</div>', unsafe_allow_html=True)
    st.dataframe(category_totals, use_container_width=True, hide_index=True)

    chart_data = category_totals.set_index("Category")
    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        st.markdown('<div class="section-title">Bar Chart</div>', unsafe_allow_html=True)
        st.bar_chart(chart_data)

    with chart_col2:
        st.markdown('<div class="section-title">Pie Chart</div>', unsafe_allow_html=True)
        st.pyplot(
            category_totals.plot.pie(
                y="Amount",
                labels=category_totals["Category"],
                autopct="%1.1f%%",
                legend=False,
                figsize=(5, 5),
                ylabel="",
            ).figure
        )

    st.markdown('<div class="section-title">Recent Transactions</div>', unsafe_allow_html=True)
    st.dataframe(expenses.head(5), use_container_width=True, hide_index=True)


def main():
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon=":bar_chart:",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    initialize_csv_files()
    setup_session_state()
    apply_styles()

    if not st.session_state.logged_in:
        show_login_page()
        return

    show_sidebar()
    if st.session_state.page == "Add Expense":
        show_add_expense()
    elif st.session_state.page == "Analytics":
        show_analytics()
    else:
        show_dashboard()


if __name__ == "__main__":
    main()
