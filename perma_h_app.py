import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="PERMA-H Radar", page_icon="📊", layout="wide")

st.title("📊 PERMA-H Reflection – Radar Chart")

st.markdown(
    "Enter (or adjust) your scores for each statement (1–10). "
    "Category scores are averaged and shown on the radar."
)

# --- Default values for sliders ---
# Default values for each question (1-10 scale)
defaults = {
    # Positive Emotion (P)
    1: 5, 2: 5, 3: 5,
    # Engagement (E)
    4: 5, 5: 5, 6: 5,
    # Relationships (R)
    7: 5, 8: 5, 9: 5,
    # Meaning (M)
    10: 5, 11: 5, 12: 5,
    # Accomplishment (A)
    13: 5, 14: 5, 15: 5,
    # Health (H)
    16: 5, 17: 5, 18: 5,
}

# --- Sidebar inputs ---
with st.sidebar:
    st.header("Enter Scores (1–10)")
    answers = {}
    sections = {
        "Positive Emotion (P)": [1, 2, 3],
        "Engagement (E)": [4, 5, 6],
        "Relationships (R)": [7, 8, 9],
        "Meaning (M)": [10, 11, 12],
        "Accomplishment (A)": [13, 14, 15],
        "Health (H)": [16, 17, 18],
    }
    # --- Add dictionary mapping question number to question text ---
    question_texts = {
        1: "I have a sense of joy and contentment in my daily life.",
        2: "I experience positive emotions regularly.",
        3: "I feel optimistic about my future.",
        4: "I am deeply interested and engaged in what I do.",
        5: "I often lose track of time when involved in activities I enjoy.",
        6: "I feel absorbed in my work or hobbies.",
        7: "I have strong and supportive relationships.",
        8: "I feel connected to others.",
        9: "I have people I can rely on in times of need.",
        10: "I believe my life has meaning and purpose.",
        11: "I contribute to something greater than myself.",
        12: "I feel that what I do in life is valuable.",
        13: "I set goals and accomplish them.",
        14: "I feel a sense of achievement from my efforts.",
        15: "I am proud of what I have accomplished.",
        16: "I take care of my physical health.",
        17: "I have healthy habits (e.g., exercise, sleep, nutrition).",
        18: "I feel energetic and physically well.",
    }
    for section, qs in sections.items():
        st.subheader(section)
        for q in qs:
            # Show full question text above the slider
            st.markdown(f"**Q{q}. {question_texts[q]}**")
            answers[q] = st.slider(
                f"Q{q}", 1, 10, int(defaults[q]), key=f"q{q}", label_visibility="collapsed"
            )

# --- Compute category averages ---
def avg(qs): 
    return float(np.mean([answers[q] for q in qs]))

category_names = list(sections.keys())
category_scores = [avg(sections[name]) for name in category_names]

# Ensure clockwise PERMA-H order starting at top
category_names = [
    "Positive Emotion (P)",
    "Engagement (E)",
    "Relationships (R)",
    "Meaning (M)",
    "Accomplishment (A)",
    "Health (H)",
]
subtitles = {
    "Positive Emotion (P)": "Enjoyment, happiness",
    "Engagement (E)": "Absorption in activities",
    "Relationships (R)": "Social connections",
    "Meaning (M)": "Purpose in life",
    "Accomplishment (A)": "Achievements, success",
    "Health (H)": "Physical and mental well-being",
}
labels_comp = [f"P (Positive Emotion)\n{subtitles['Positive Emotion (P)']}",
               f"E (Engagement)\n{subtitles['Engagement (E)']}",
               f"R (Relationships)\n{subtitles['Relationships (R)']}",
               f"M (Meaning)\n{subtitles['Meaning (M)']}",
               f"A (Accomplishment)\n{subtitles['Accomplishment (A)']}",
               f"H (Health)\n{subtitles['Health (H)']}"]
# Recompute scores in this explicit order
category_scores = [avg(sections[name]) for name in category_names]

# --- Table of scores ---
scores_df = pd.DataFrame({
    "Category": category_names,
    "Average (1–10)": [round(s, 2) for s in category_scores]
})

col1, col2 = st.columns([2, 1], gap="large")

with col1:
    # --- Radar chart with Matplotlib ---
    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True))
    # Start from top (90°) and go clockwise
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)

    # Angles for each category
    angles = np.linspace(0, 2 * np.pi, len(category_scores), endpoint=False)
    angles = np.concatenate([angles, angles[:1]])
    values = np.array(category_scores)
    values = np.concatenate([values, values[:1]])

    ax.plot(angles, values, linewidth=2)
    ax.fill(angles, values, alpha=0.3)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels_comp, fontsize=11)

    # Radial ticks 0..10 and light grid
    ax.set_rgrids([2, 4, 6, 8, 10], angle=90)
    ax.set_ylim(0, 10)
    ax.grid(True, linestyle='--', alpha=0.4)
    ax.set_title("PERMA-H Well-Being Wheel", pad=20)

    st.pyplot(fig, use_container_width=True)

    st.markdown("""
    **Interpretation:**
    - **8–10**: High well-being in this domain
    - **5–7**: Moderate well-being; potential area for growth
    - **1–4**: Low well-being; consider focusing on this area
    """)

    # Download chart as PNG
    import io
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=200)
    st.download_button(
        "Download chart as PNG",
        data=buf.getvalue(),
        file_name="permah_radar.png",
        mime="image/png",
    )

with col2:
    st.subheader("Category Averages")
    st.dataframe(scores_df, use_container_width=True)

    # Download data
    st.download_button(
        "Download data (CSV)",
        data=scores_df.to_csv(index=False),
        file_name="permah_scores.csv",
        mime="text/csv",
    )

st.markdown("---")
st.caption("Tip: Use the sidebar to adjust answers and see your radar update instantly.")