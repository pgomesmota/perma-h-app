import streamlit as st
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# --- APP palette ---
BRAND_PRIMARY = "#0B3D61"   # deep navy/blue
BRAND_ACCENT  = "#0099B8"   # teal/cyan accent
BRAND_LIGHT   = "#E9F4F9"   # very light blue background
BRAND_MID     = "#A9C7D8"   # mid light for tracks/borders

st.markdown(
    f"""
    <style>
      .block-container {{padding-top: 0.75rem; padding-bottom: 0.5rem; max-width: 1200px;}}
      section[data-testid="stSidebar"] {{width: 360px;}}
      /* Right-side panel styling aligned with brand */
      /* Removed .perma-panel styling */
      /* Slider theming (transparent background, visible track line) */
      .stSlider [data-baseweb="slider"] > div {{ background: transparent; border-bottom: 2px solid {BRAND_MID}; }}
      .stSlider [data-baseweb="slider"] div[role="slider"] {{ background: {BRAND_ACCENT}; border: 2px solid {BRAND_PRIMARY}; box-shadow: none; }}
      .stSlider [data-baseweb="slider"] > div > div {{ background: {BRAND_ACCENT}; }}
      /* Slider value label color */
      .stSlider [data-baseweb="slider"] span[role="tooltip"] {{ color: {BRAND_PRIMARY} !important; background: transparent !important; }}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    f"""
    <style>
      html body [class*="tooltip"] {{
        color: {BRAND_PRIMARY} !important;
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
      }}
    </style>
    """,
    unsafe_allow_html=True,
)

st.set_page_config(page_title="PERMA-H Radar", page_icon="📊", layout="wide")

st.title("PERMA-H – Radar Chart")

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
        with st.expander(section, expanded=False):
            for q in qs:
                st.markdown(f"**Q{q}. {question_texts[q]}**")
                answers[q] = st.slider(
                    f"Q{q}", 1, 10, int(defaults[q]), key=f"q{q}", label_visibility="collapsed"
                )

# --- Compute category averages ---
def avg(qs): 
    return float(np.mean([answers[q] for q in qs]))

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

col1, col2 = st.columns([1, 1], gap="large")

with col1:
    # --- Radar chart with Matplotlib ---
    fig, ax = plt.subplots(figsize=(6.8, 6.8), subplot_kw=dict(polar=True))
    # Start from top (90°) and go clockwise
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)

    # Angles for each category
    angles = np.linspace(0, 2 * np.pi, len(category_scores), endpoint=False)
    angles = np.concatenate([angles, angles[:1]])
    values = np.array(category_scores)
    values = np.concatenate([values, values[:1]])

    ax.plot(angles, values, linewidth=2.5, color=BRAND_PRIMARY)
    ax.fill(angles, values, alpha=0.35, color=BRAND_ACCENT)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels_comp, fontsize=10)

    # Radial ticks 0..10 and light grid
    ax.set_rgrids([2, 4, 6, 8, 10], angle=90)
    for lbl in ax.yaxis.get_ticklabels():
        lbl.set_color(BRAND_PRIMARY)
    ax.set_ylim(0, 10)
    ax.grid(True, linestyle='--', alpha=0.4)
    ax.tick_params(colors=BRAND_PRIMARY)
    ax.set_title("PERMA-H Well-Being Wheel", pad=16, color=BRAND_PRIMARY, fontsize=16)

    st.pyplot(fig, use_container_width=True)

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
    # Removed perma-panel div wrapper
    st.markdown(f"### <span style='color:{BRAND_PRIMARY}'>Category Averages</span>", unsafe_allow_html=True)

    # Modern horizontal bullet-style chart
    fig_avg, ax_avg = plt.subplots(figsize=(4.4, 3.8))
    y = np.arange(len(category_names))

    # Background tracks to 10
    ax_avg.barh(y, [10]*len(category_names), height=0.5, color=BRAND_LIGHT, edgecolor="none")

    # Foreground value bars
    bars = ax_avg.barh(y, category_scores, height=0.5, color=BRAND_ACCENT, edgecolor="none")

    # Labels and styling
    ax_avg.set_yticks(y)
    ax_avg.set_yticklabels([n.split(" (")[0] for n in category_names], fontsize=11)
    for lbl in ax_avg.get_yticklabels():
        lbl.set_color(BRAND_PRIMARY)
    ax_avg.set_xlim(0, 10)
    ax_avg.invert_yaxis()
    ax_avg.set_xlabel("")
    ax_avg.set_ylabel("")
    ax_avg.spines['top'].set_visible(False)
    ax_avg.spines['right'].set_visible(False)
    ax_avg.spines['left'].set_visible(False)
    ax_avg.spines['bottom'].set_visible(False)
    ax_avg.tick_params(axis='x', bottom=False, labelbottom=False)

    # Value badges
    for i, v in enumerate(category_scores):
        ax_avg.text(v + 0.25, i, f"{v:.1f}", va='center', fontsize=13, fontweight='bold', color=BRAND_PRIMARY)

    st.pyplot(fig_avg, use_container_width=True)

    st.markdown(
        """
        **Interpretation**  
        • **8–10** High well-being  
        • **5–7** Moderate; potential to grow  
        • **1–4** Low; consider focusing here
        """
    )

st.markdown("---")
st.caption("Tip: Use the sidebar to adjust answers and see your radar update instantly.")