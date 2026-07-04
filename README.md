# 🏭 Blast Furnace Digital Twin & Process Simulator

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.20+-FF4B4B.svg)
![Plotly](https://img.shields.io/badge/Plotly-Graphing-3f4f75.svg)
![NumPy](https://img.shields.io/badge/NumPy-Data-013243.svg)

## 📌 Overview
This project is an interactive, SCADA/HMI-inspired digital twin of a modern Blast Furnace (BF). Designed with R&D and integrated steel plant operations in mind, this application simulates critical ironmaking process parameters in real-time. It visualizes the internal state of the furnace—such as raceway temperature and cohesive zone shifts—while calculating essential Key Performance Indicators (KPIs) like fuel rate, productivity, and carbon emissions.

## 🏗️ Technical Architecture
The application leverages a lightweight but powerful modern data stack:
* **Frontend & State Management (Streamlit):** Utilizes Streamlit with custom CSS injection to create an enterprise-grade, dark-themed industrial dashboard.
* **Data Manipulation (Pandas):** Handles KPI arrays and prepares real-time data for CSV export and simulation tracking.
* **Geometric Modeling (NumPy):** Constructs the high-fidelity 2D internal profile of the blast furnace dynamically. Cosine easing functions ensure mathematically smooth transitions between the throat, stack, belly, bosh, and hearth.
* **Dynamic Visualization (Plotly):** Renders the physical phenomena inside the reactor. Elements like raceway glow intensity and liquid levels respond instantly to changes in input parameters.

## 🔬 Metallurgical Heuristics & Process Logic
The core engine relies on foundational ironmaking principles, utilizing heuristic approximations to simulate furnace behavior dynamically.

### 1. Raceway Adiabatic Flame Temperature (RAFT)
RAFT is a critical indicator of hearth thermal state. The simulation models the endothermic impact of blast moisture and Pulverized Coal Injection (PCI), balanced against the sensible heat of the Hot Blast Temperature (HBT).

$$\text{RAFT} = 2180 + 0.9(\text{HBT} - 1000) - 9(\text{Moisture} - 10) - 1.1(\text{PCI} - 100)$$

*Implementation Note: Triggers automated alarms if RAFT drops below the critical stability threshold of 2100°C.*

### 2. Fuel Rate & Carbon Emissions
Total reducing agent rate is calculated to benchmark furnace efficiency, while CO₂ emissions are estimated based on the specific carbon content and oxidation pathways of coke versus PCI coal.

$$\text{Total Fuel Rate} = \text{Coke Rate} + \text{PCI Rate}$$

$$\text{CO}_2 \text{ Emission} = (\text{Coke Rate} \times 3.05) + (\text{PCI Rate} \times 2.65)$$

### 3. Cohesive Zone Dynamics
The cohesive (softening-melting) zone is represented visually and mathematically. Its vertical position shifts based on:
* **Burden Ratio (Ore/Coke):** Higher ratios reduce gas permeability, deepening the cohesive zone root.
* **Fuel Rate:** Lower fuel rates reduce coke slit permeability, shifting the melting zone downward.

## 🚀 Key Features
* **Dynamic 2D Cross-Section:** A live mathematical rendering of the furnace interior that reacts to thermal and burden inputs.
* **"What-If" Simulation Engine:** Allows engineers to test parameter deltas (e.g., +50°C HBT) and instantly view the variance in fuel consumption and CO₂ output.
* **Emissions Benchmarking:** Visual comparison of current simulated CO₂ outputs against best-in-class and regulatory industry standards.
* **Industrial Alarms:** Automated `warning` and `error` states for inefficient or dangerous operating conditions.
* **Data Export:** One-click CSV generation for simulation timestamping and offline analysis.

## 💻 Installation & Usage

**Step 1: Clone the repository**
```bash
git clone [https://github.com/YourUsername/bf-digital-twin.git](https://github.com/YourUsername/bf-digital-twin.git)
cd bf-digital-twin
```

**Step 2: Install dependencies**
```bash
pip install -r requirements.txt
```

**Step 3: Run the dashboard**
```bash
streamlit run app.py
```

---

## 👨‍💻 Author
**Sourish Roy** *Metallurgical & Materials Engineering | Jadavpur University* Connect with me on [LinkedIn](https://www.linkedin.com/in/sourishroy1609) or view my other technical projects here on GitHub.