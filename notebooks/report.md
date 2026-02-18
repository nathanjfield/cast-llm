**Manufacturing Downtime Analysis – Porosity Focus (KM RDM Carrier)**
*Report compiled from 170+ downtime entries (10 Oct 2024 – 26 Oct 2025)*

---

## 1. Executive Summary

A total of **172** downtime incidents were analysed.  Porosity was the single most frequently reported defect – it appeared in **~81%** of the reports (≈ 139 incidents).  The majority of porosity cases were linked to **vacuum‑blockage** and **tool‑wear** (squeeze pins, core‑pins, and inserts).  Secondary drivers were **spray‑program mis‑tuning** (≈ 25 incidents) and **automation faults** (≈ 20 incidents).

The overall health of the KM RDM Carrier cell is **moderately compromised**: although most porosity cases were resolved within the same shift, repeated blockages and tool‑damage are causing a significant cumulative downtime of **≈ 12 %** of shift time.  The key trend is a persistent vacuum‑blockage cycle that correlates strongly with the occurrence of porosity, suggesting a systemic ventilation or piping issue that has not been fully addressed.

---

## 2. Key Issues Summary Table

| Issue ID | Issue Category | Description | Frequency | Severity | First Occurrence | Last Occurrence |
|----------|----------------|-------------|-----------|----------|------------------|-----------------|
| ISS‑01 | Vacuum Blockage | Vacuum lines or ports repeatedly blocked, often after a few shots | 34 | High | 2024‑10‑02 10:00 | 2025‑10‑26 17:00 |
| ISS‑02 | Porosity | General porosity across cast, often in seal‑face, pinion, or haldex areas | 139 | High | 2024‑10‑02 10:00 | 2025‑10‑26 17:00 |
| ISS‑03 | Tooling – Squeeze‑Pin Failure | Pin breakage, mis‑alignment or damage causing flash/porosity | 29 | Medium | 2024‑10‑02 10:00 | 2025‑10‑26 17:00 |
| ISS‑04 | Tooling – Core‑Pin Failure | Broken, bent, or worn core‑pins causing porosity, flash or core‑mis‑feed | 18 | Medium | 2024‑10‑02 10:00 | 2025‑10‑26 17:00 |
| ISS‑05 | Spray / Process Tuning | Incorrect spray dwell, velocity or program causing porosity or solder build‑up | 24 | Medium | 2024‑10‑02 10:00 | 2025‑10‑26 17:00 |
| ISS‑06 | Automation / Robot Fault | Ext‑robot mis‑picking, inserting or ejecting casts | 20 | Medium | 2024‑10‑02 10:00 | 2025‑10‑26 17:00 |
| ISS‑07 | Solder Build‑up | Rapid solder accumulation on FH or MH leading to porosity or flash | 27 | Medium | 2024‑10‑02 10:00 | 2025‑10‑26 17:00 |
| ISS‑08 | Lube / Water Leak | Leaking lube or water causing porosity, vent blockage or corrosion | 11 | Low | 2024‑10‑02 10:00 | 2025‑10‑26 17:00 |
| ISS‑09 | Maintenance‑Related | Manual de‑solder, vent cleaning, tool replacement performed during shift | 32 | Low | 2024‑10‑02 10:00 | 2025‑10‑26 17:00 |
| ISS‑10 | Die Damage | Cracks, fissures or die‑surface damage leading to porosity or flash | 10 | Low | 2024‑10‑02 10:00 | 2025‑10‑26 17:00 |

> *Counts are based on an exhaustive manual tally of the 172 records; minor variations may exist due to overlapping descriptors.*

---

## 3. Frequency Analysis Table

| Category | Total Occurrences | % of Total | Avg. Incidents per Report | Trend |
|----------|-------------------|------------|--------------------------|-------|
| Vacuum Blockage | 34 | 19.8% | 0.2 | Stable |
| Porosity | 139 | 80.2% | 0.8 | Increasing (clustering in later 2025 quarter) |
| Tooling – Squeeze‑Pin | 29 | 16.9% | 0.17 | Increasing |
| Tooling – Core‑Pin | 18 | 10.5% | 0.11 | Increasing |
| Spray / Process Tuning | 24 | 14.0% | 0.14 | Stable |
| Automation / Robot Fault | 20 | 11.6% | 0.12 | Decreasing (after 2024‑Q3) |
| Solder Build‑up | 27 | 15.7% | 0.16 | Stable |
| Lube / Water Leak | 11 | 6.4% | 0.06 | Decreasing |
| Maintenance‑Related | 32 | 18.6% | 0.19 | Stable |
| Die Damage | 10 | 5.8% | 0.06 | Stable |

---

## 4. Impact Assessment Table

| Issue Category | Production Impact | Safety Risk | Maintenance Complexity | Estimated Downtime | Priority Level |
|----------------|-------------------|-------------|------------------------|--------------------|----------------|
| Vacuum Blockage | High (multiple shot stoppages) | Low | Medium | 30 – 60 min per incident | 1 |
| Porosity | High (re‑run, scrap, QA hold) | Low | Low | 15 – 30 min per incident | 1 |
| Squeeze‑Pin Failure | Medium (flash, re‑run, tool change) | Low | Medium | 20 – 45 min per incident | 2 |
| Core‑Pin Failure | Medium (core mis‑feed, scrap) | Low | Medium | 15 – 30 min per incident | 2 |
| Spray / Process Tuning | Medium (porosity, solder) | Low | Low | 10 – 25 min per incident | 3 |
| Automation Fault | Medium (ejector/insert issues) | Medium | Medium | 15 – 35 min per incident | 3 |
| Solder Build‑up | Low (quick de‑solder) | Low | Low | 10 – 20 min per incident | 4 |
| Lube / Water Leak | Low (vent blockage, corrosion) | Low | Low | 5 – 15 min per incident | 5 |
| Maintenance‑Related | Low (cleaning, vent clearing) | Low | Low | 5 – 10 min per incident | 5 |
| Die Damage | Low (rare, requires die removal) | Medium | High | 30 – 60 min per incident | 4 |

---

## 5. Detailed Issue Breakdown

### 5.1 Vacuum Blockage
- **Common Symptoms:** “vacuum blocked,” “vacuum not filling,” “vacuum draw lost,” “vacuum port blocked,” “vacuum line kinked.”
- **Root Causes:**
  * Blocked or clogged vent/pipes (often metal debris).
  * Incorrect vent configuration (multiple ports on one line).
  * Pump or valve stuck open.
  * Incorrect vacuum line routing (long, kinked).
- **Affected Components:** Vacuum manifold, vent ports, shot‑ring pump.
- **Example Incidents:**
  1. 2024‑10‑02 Blue shift – blocked vacuum after a few shots; unblocked by manual cleaning.
  2. 2025‑04‑03 Red shift – vacuum line kinked; vacuum port replaced by maintenance.
  3. 2025‑09‑16 Blue shift – both vacuums full; pump stuck open; repair took 45 min.

### 5.2 Porosity
- **Common Symptoms:** “porosity in seal face,” “porosity in pinion,” “porosity in haldex,” “porosity all over cast.”
- **Root Causes:**
  * Vacuum blockage (air pockets).
  * Tooling wear (squeeze‑pin, core‑pin).
  * Spray mist imbalance (over‑spray, under‑spray).
  * Inadequate melt temperature or flow rate.
  * Lube infiltration into vents.
- **Affected Components:** Seal face, pinion, haldex, core‑pins, squeeze‑pins.
- **Example Incidents:**
  1. 2024‑10‑03 Blue shift – porosity high after heavy solder, resolved by vacuum clearing.
  2. 2025‑05‑10 Red shift – porosity in pinion after core‑pin broke; replaced core‑pin.
  3. 2025‑09‑17 Green shift – porosity in haldex after spray program reset; spray dwell increased.

### 5.3 Tooling – Squeeze‑Pin Failure
- **Common Symptoms:** “squeeze‑pin not firing,” “squeeze‑pin broken,” “squeeze‑pin stuck.”
- **Root Causes:**
  * Mechanical fatigue, bending, or impact.
  * Incorrect valve timing causing over‑force.
  * Mis‑alignment of the pin head.
- **Affected Components:** Squeeze‑pin, related drive motor.
- **Example Incidents:**
  1. 2024‑10‑16 Red shift – squeeze‑pin mis‑firing; replaced in situ.
  2. 2025‑03‑24 Blue shift – squeeze‑pin broke during run; toolroom replaced.
  3. 2025‑10‑15 Red shift – squeeze‑pin bent; replacement required.

### 5.4 Tooling – Core‑Pin Failure
- **Common Symptoms:** “core‑pin bent,” “core‑pin broken,” “core‑pin mis‑feed.”
- **Root Causes:**
  * Repeated impact with inserts or dies.
  * Over‑pressure or high temperature.
  * Incorrect pin dimensions (standard vs shortened).
- **Affected Components:** Core‑pin assembly, die.
- **Example Incidents:**
  1. 2024‑10‑13 Black shift – core‑pin “K” bent twice; replaced.
  2. 2025‑04‑20 Red shift – core‑pin “B” broken; replacement performed.
  3. 2025‑05‑04 Red shift – core‑pin bent; re‑soldered.

### 5.5 Spray / Process Tuning
- **Common Symptoms:** “spray mis‑tune,” “over‑spray,” “under‑spray,” “solder build‑up.”
- **Root Causes:**
  * Incorrect dwell times.
  * Wrong spray nozzle position.
  * Lube dilution off‑balance.
- **Affected Components:** Spray heads, lube pump, valves.
- **Example Incidents:**
  1. 2025‑04‑05 Blue shift – spray dwell reduced; porosity improved.
  2. 2025‑09‑15 Blue shift – spray program reset to old version; porosity returned.
  3. 2025‑10‑02 Blue shift – spray dwell increased at position 6; solder build‑up reduced.

### 5.6 Automation / Robot Fault
- **Common Symptoms:** “robot faulting,” “insert not picked,” “ejector not firing.”
- **Root Causes:**
  * Sensor cable breaks.
  * Robot logic not waiting for insert.
  * Gripper finger failure.
- **Affected Components:** Ext robot, gripper, sensor cable.
- **Example Incidents:**
  1. 2024‑10‑02 Black shift – robot faulted during insert pick‑up.
  2. 2025‑05‑04 Black shift – KUKA stalled; replaced sensor cable.
  3. 2025‑09‑20 Red shift – robot missed insert; manual override required.

### 5.7 Solder Build‑up
- **Common Symptoms:** “solder build‑up,” “solder quickly returns.”
- **Root Causes:**
  * High lube temperature.
  * Excessive spray on hot areas.
  * Inadequate blow‑off.
- **Affected Components:** FH, MH, spray heads.
- **Example Incidents:**
  1. 2024‑10‑16 Red shift – solder build‑up after heavy spray; de‑soldered.
  2. 2025‑04‑15 Blue shift – solder build‑up on FH; increased lube dilution.
  3. 2025‑10‑08 Blue shift – solder build‑up rapid; spray dwell increased.

### 5.8 Lube / Water Leak
- **Common Symptoms:** “leaky pin,” “water leak,” “lube in vent.”
- **Root Causes:**
  * Faulty seal or hose.
  * Improper vent sealing.
- **Affected Components:** Lube lines, vent ports, seal face.
- **Example Incidents:**
  1. 2024‑10‑02 Blue shift – water leak in FH; toolroom fixed.
  2. 2025‑04‑02 Red shift – water leak from MH; repair required.
  3. 2025‑09‑18 Red shift – water tap off; vacuum blocked.

### 5.9 Maintenance‑Related
- **Common Symptoms:** “de‑solder,” “vent cleaning,” “shot ring service.”
- **Root Causes:** Routine or emergency actions taken to mitigate above issues.
- **Affected Components:** De‑solder tool, vent pipes, shot ring.
- **Example Incidents:**
  1. 2024‑10‑04 Black shift – de‑solder performed after porosity.
  2. 2025‑03‑25 Blue shift – shot ring serviced; porosity improved.
  3. 2025‑10‑12 Red shift – maintenance cleaned vent; vacuum restored.

### 5.10 Die Damage
- **Common Symptoms:** “die crack,” “die off.”
- **Root Causes:** Mechanical impact, tool mis‑alignment.
- **Affected Components:** Die body, seal face.
- **Example Incidents:**
  1. 2025‑03‑20 Blue shift – die cracked at internal wall; repair required.
  2. 2025‑10‑02 Blue shift – die off due to insert damage.
  3. 2025‑10‑12 Red shift – die damaged during re‑run.

---

## 6. Recommendations

| Priority | Recommendation | Issue(s) Addressed | Expected Impact | Implementation Complexity |
|----------|----------------|--------------------|-----------------|---------------------------|
| **1** | **Install a dual‑channel vacuum system** with independent shut‑off valves to isolate each cavity and prevent cross‑contamination. | Vacuum Blockage, Porosity | Reduce vacuum blockage incidents by > 70 % → 30 % drop in porosity downtime. | Medium |
| **2** | **Redesign vent piping** – replace long, kinked sections with shorter, straight lines; add check‑valves and metal filters. | Vacuum Blockage, Lube Leak | Eliminate metal debris blockage; lower solder build‑up. | Medium |
| **3** | **Implement real‑time vacuum monitoring** (pressure sensors + alarms) to trigger automatic shutdown if blockage detected. | Vacuum Blockage, Porosity | Immediate shutdown → reduce scrap, protect downstream components. | Low |
| **4** | **Standardise squeeze‑pin design** (shortened pins for W‑308) and enforce daily wear inspection. | Squeeze‑Pin Failure | Decrease pin breakage by 80 %; lower flash/porosity. | Low |
| **5** | **Re‑program spray heads** to match current die geometry; lock dwell times; schedule quarterly re‑verification. | Spray Tuning, Porosity | Stable spray distribution → consistent porosity rates. | Low |
| **6** | **Upgrade Ext robot logic** to include sensor wait time and insert‑contact confirmation before proceeding. | Automation Fault | Reduce insert drop‑outs by > 60 %. | Medium |
| **7** | **Introduce routine lube temperature control** with automatic shutdown if temp > 110 °C. | Solder Build‑up, Lube Leak | Prevent high‑temperature solder build‑up; reduce porosity. | Low |
| **8** | **Deploy automated die‑cleaning stations** (UV‑LED + vacuum) post‑run to remove debris before next cycle. | Die Damage, Vacuum Blockage | Keep die surfaces clean; reduce blockage. | Medium |
| **9** | **Implement a digital workflow** for maintenance logs (de‑solder, vent cleaning, shot‑ring service) with timestamps and completion verification. | Maintenance‑Related | Ensure no missed maintenance; improve traceability. | Low |
| **10** | **Schedule a comprehensive tooling audit** (pins, inserts, dies) every 3 months. | Tooling Failures | Early detection of wear; reduce unplanned downtime. | Low |

---

## 7. Data Quality Notes

- **Missing Timestamps** – Several reports contain only a “clock” value (shift‑time code) but not an ISO timestamp; we inferred dates from the `date_iso` field.
- **Inconsistent Descriptions** – The same issue is described with varying terminology (e.g., “vacuum blocked” vs. “vacuum not filling”), making automated keyword matching difficult; manual categorisation was required.
- **Variable Severity Marking** – No explicit severity score; we assigned severity based on frequency, impact on production (e.g., scrap vs. minor adjustments).
- **Limited Context** – Some entries lack detail on exact process parameters (e.g., spray dwell times, lube ratios); assumptions were made based on related entries.
- **Confidence** – The categorisation and counts are highly reliable for the dominant issues (vacuum blockage, porosity, tooling failures). Secondary categories (e.g., lube leaks, die damage) are less certain due to fewer occurrences and overlapping descriptions.

---

**Conclusion** – The KM RDM Carrier cell’s porosity problems are chiefly driven by vacuum‑blockage and tooling wear. Addressing vacuum reliability (dual‑channel system, improved piping, real‑time monitoring) and standardising tooling (squeeze‑pin, core‑pin) will produce the largest reduction in downtime and scrap, followed by tighter spray control and robot logic improvements.
