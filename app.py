import os
import time

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from google import genai


# ==================================================
# PAGE CONFIGURATION
# ==================================================

st.set_page_config(
    page_title="AI Sales Lead Qualification Agent",
    page_icon="📊",
    layout="wide"
)


# ==================================================
# CUSTOM CSS
# ==================================================

st.markdown(
    """
    <style>

    .stApp {
        background: linear-gradient(
            135deg,
            #f5f7fa 0%,
            #e8eef7 100%
        );
    }

    .main-title {
        font-size: 42px;
        font-weight: 700;
        margin-bottom: 5px;
    }

    .subtitle {
        font-size: 18px;
        color: #555555;
        margin-bottom: 30px;
    }

    .metric-card {
        background: white;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        text-align: center;
    }

    .metric-title {
        font-size: 16px;
        color: #666666;
    }

    .metric-value {
        font-size: 32px;
        font-weight: 700;
        margin-top: 5px;
    }

    .section-title {
        font-size: 24px;
        font-weight: 700;
        margin-top: 30px;
        margin-bottom: 15px;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ==================================================
# LOAD ENVIRONMENT VARIABLES
# ==================================================

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if api_key:
    client = genai.Client(api_key=api_key)
else:
    client = None


# ==================================================
# TITLE
# ==================================================

st.markdown(
    '<div class="main-title">📊 AI Sales Lead Qualification Agent</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Automatically qualify sales leads using scoring rules and Gemini AI.'
    '</div>',
    unsafe_allow_html=True
)


# ==================================================
# SIDEBAR
# ==================================================

st.sidebar.header("📁 Lead Data")

uploaded_file = st.sidebar.file_uploader(
    "Upload CSV file",
    type=["csv"]
)


# ==================================================
# LOAD CSV
# ==================================================

df = None

if uploaded_file is not None:

    try:
        df = pd.read_csv(uploaded_file)

    except Exception as e:

        st.error(
            f"Unable to read the uploaded CSV file: {e}"
        )

else:

    default_file = "leads-2.csv"

    if os.path.exists(default_file):

        try:
            df = pd.read_csv(default_file)

        except Exception as e:

            st.error(
                f"Unable to read {default_file}: {e}"
            )


# ==================================================
# REQUIRED COLUMNS
# ==================================================

required_columns = [
    "Name",
    "Company",
    "Budget",
    "Requirement",
    "Timeline",
    "Decision_Maker"
]


# ==================================================
# SCORING FUNCTIONS
# ==================================================

def calculate_budget_score(budget):

    try:
        budget = float(budget)
    except:
        return 0

    if budget >= 150000:
        return 30

    elif budget >= 100000:
        return 25

    elif budget >= 50000:
        return 20

    elif budget >= 25000:
        return 10

    else:
        return 5


def calculate_requirement_score(requirement):

    if pd.notna(requirement) and str(requirement).strip():

        return 30

    return 0


def calculate_timeline_score(timeline):

    if pd.isna(timeline):
        return 0

    timeline = str(timeline).lower().strip()

    if (
        "week" in timeline
        or "1 month" in timeline
        or "2 month" in timeline
    ):
        return 20

    elif "3 month" in timeline:
        return 15

    elif (
        "4 month" in timeline
        or "5 month" in timeline
        or "6 month" in timeline
    ):
        return 10

    elif "6+" in timeline:
        return 5

    else:
        return 0


def calculate_decision_maker_score(decision_maker):

    if pd.isna(decision_maker):
        return 0

    if str(decision_maker).lower().strip() == "yes":
        return 20

    return 0


def classify_lead(score):

    if score >= 75:
        return "Hot"

    elif score >= 50:
        return "Warm"

    else:
        return "Cold"


# ==================================================
# GEMINI AI SUMMARY FUNCTION
# ==================================================

def generate_lead_summary(row):

    prompt = f"""
You are a sales assistant.

Analyse this sales lead and write a short professional summary.

Lead Name: {row['Name']}
Company: {row['Company']}
Budget: ₹{row['Budget']}
Requirement: {row['Requirement']}
Timeline: {row['Timeline']}
Decision Maker: {row['Decision_Maker']}
Qualification Score: {row['Qualification_Score']}
Classification: {row['Classification']}

Write only a short summary in 2 sentences.
"""

    for attempt in range(3):

        try:

            response = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=prompt
            )

            return response.text

        except Exception as e:

            if "503" in str(e) and attempt < 2:

                time.sleep(3)

            else:

                return (
                    "Gemini is temporarily unavailable. "
                    "Please try again later."
                )


# ==================================================
# SUGGEST NEXT ACTION
# ==================================================

def suggest_next_action(row):

    if row["Classification"] == "Hot":

        if str(row["Decision_Maker"]).lower() == "yes":

            return (
                "Schedule an immediate sales call and "
                "prepare a tailored proposal."
            )

        else:

            return (
                "Contact the lead quickly and "
                "identify the decision maker."
            )

    elif row["Classification"] == "Warm":

        return (
            "Follow up with the lead to understand "
            "requirements and confirm the purchase timeline."
        )

    else:

        return (
            "Nurture the lead and follow up later "
            "when the purchase need becomes active."
        )


# ==================================================
# PROCESS CSV
# ==================================================

if df is not None:

    # ==================================================
    # CHECK REQUIRED COLUMNS
    # ==================================================

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:

        st.error(
            f"Missing required columns: {missing_columns}"
        )

    else:

        # ==================================================
        # CALCULATE SCORES
        # ==================================================

        df["Budget_Score"] = df["Budget"].apply(
            calculate_budget_score
        )

        df["Requirement_Score"] = df["Requirement"].apply(
            calculate_requirement_score
        )

        df["Timeline_Score"] = df["Timeline"].apply(
            calculate_timeline_score
        )

        df["Decision_Maker_Score"] = df["Decision_Maker"].apply(
            calculate_decision_maker_score
        )


        # ==================================================
        # TOTAL SCORE
        # ==================================================

        df["Qualification_Score"] = (
            df["Budget_Score"]
            + df["Requirement_Score"]
            + df["Timeline_Score"]
            + df["Decision_Maker_Score"]
        )


        # ==================================================
        # CLASSIFICATION
        # ==================================================

        df["Classification"] = df["Qualification_Score"].apply(
            classify_lead
        )


        # ==================================================
        # SUMMARY COUNTS
        # ==================================================

        total_leads = len(df)

        hot_leads = len(
            df[df["Classification"] == "Hot"]
        )

        warm_leads = len(
            df[df["Classification"] == "Warm"]
        )

        cold_leads = len(
            df[df["Classification"] == "Cold"]
        )


        # ==================================================
        # DASHBOARD CARDS
        # ==================================================

        col1, col2, col3, col4 = st.columns(4)

        with col1:

            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">
                        Total Leads
                    </div>
                    <div class="metric-value">
                        {total_leads}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with col2:

            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">
                        🔥 Hot Leads
                    </div>
                    <div class="metric-value">
                        {hot_leads}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with col3:

            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">
                        🟡 Warm Leads
                    </div>
                    <div class="metric-value">
                        {warm_leads}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with col4:

            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">
                        🔵 Cold Leads
                    </div>
                    <div class="metric-value">
                        {cold_leads}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )


        # ==================================================
        # LEAD RESULTS
        # ==================================================

        st.markdown(
            '<div class="section-title">'
            '📋 Lead Qualification Results'
            '</div>',
            unsafe_allow_html=True
        )

        display_columns = [
            "Name",
            "Company",
            "Budget",
            "Requirement",
            "Timeline",
            "Decision_Maker",
            "Qualification_Score",
            "Classification"
        ]

        st.dataframe(
            df[display_columns],
            use_container_width=True,
            hide_index=True
        )


        # ==================================================
        # AI LEAD SUMMARY
        # ==================================================

        st.markdown(
            '<div class="section-title">'
            '🤖 AI Lead Summary'
            '</div>',
            unsafe_allow_html=True
        )

        if st.button(
            "✨ Generate AI Summary for First Lead"
        ):

            if client is None:

                st.error(
                    "Gemini API key not found. "
                    "Please check your .env file."
                )

            else:

                with st.spinner(
                    "Generating AI summary..."
                ):

                    summary = generate_lead_summary(
                        df.iloc[0]
                    )

                st.success(
                    "AI Summary Generated"
                )

                st.write(summary)


        # ==================================================
        # SUGGESTED NEXT ACTION
        # ==================================================

        st.markdown(
            '<div class="section-title">'
            '🎯 Suggested Next Action'
            '</div>',
            unsafe_allow_html=True
        )

        first_lead = df.iloc[0]

        next_action = suggest_next_action(
            first_lead
        )

        st.info(next_action)


else:

    st.info(
        "No CSV file found. Please upload a CSV file from the sidebar."
    )