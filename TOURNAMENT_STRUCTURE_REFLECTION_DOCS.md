# 2025 osu! Tournament Structure: Current State and Reflection

**Date:** January 13, 2026  
**Subject:** Technical Reflection for 2026 Tournament Planning

## Overview
This document summarizes the internal structure and technical logic of the current osu! tournament platform. It serves as a baseline for identifying areas of improvement and optimization for the 2026 tournament cycle.

---

## 1. Tournament Format and Progression
The current system implements a **Double Elimination** bracket, which provides a competitive safety net for participants:
*   **Bracket Structure**: Includes both an "Upper Bracket" for undefeated players and a "Lower Bracket" for those with one loss.
*   **Grand Finals Implementation**: A climactic final match between the Upper and Lower bracket champions.
*   **Bracket Reset Mechanism**: In the spirit of double elimination, if the Lower Bracket winner wins the first final match, a "Reset" match is automatically scheduled to determine the ultimate winner.

## 2. Seeding and Participant Management
Seeding is automated to ensure competitive fairness, utilizing a **Snake Seeding** algorithm based on the following criteria:
*   **Primary Seeding**: Qualifier placement (determined by earlier tournament rounds).
*   **Fallback Seeding**: Performance Points (PP) are used for initial placement and tie-breaking.
*   **Match Balancing**: The system automatically pads the participant list with "BYE" matches to maintain a mathematically correct bracket (powers of two).

## 3. Mappool and Technical Integration
A defining feature of the current platform is the **User-Submitted Mappool** system, allowing for player-specific strategy:
*   **Metadata Synchronization**: The system integrates directly with the osu! API to fetch real-time map statistics, including Star Rating, AR, CS, and BPM.
*   **Visual Interface**: Map details are displayed in an interactive match interface, allowing for clear pick/ban visibility.
*   **Data Integrity**: Mappool details are cached locally to ensure high performance during live match broadcasts.

## 4. Platform Infrastructure
The underlying technology stack focuses on real-time broadcast capability:
*   **Backend Logic**: Powered by a Python-based Flask framework.
*   **Data Management**: State is maintained in a centralized data file to allow for portability and ease of backup.
*   **Real-time Overlays**: Broadcasting is supported by a 1080p high-definition overlay system that updates automatically via state-polling, requiring no manual interaction from tournament directors during matches.

## 5. Strategic Reflection for 2026
Initial analysis for the 2026 cycle highlights several areas for evolution:
*   **Scaling & Reliability**: Moving toward a more robust database system to prevent data race conditions during high-concurrency events.
*   **Format Flexibility**: Decoupling bracket logic to support varied formats such as Swiss System or Round Robin.
*   **Infrastructure Modernization**: Migrating the frontend architecture to a component-based system to allow for easier visual customization and faster deployment.
*   **Advanced Permissions**: Implementing a granular role-based access control system for multi-staff tournament events.

---
*Prepared by the SWEF Technical Team for internal review.*
