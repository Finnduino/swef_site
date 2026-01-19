# osu! Tournament Structure Reflection (Current State)

This document provides a comprehensive overview of the current tournament system's structure, logic, and technical implementation. This reflection serves as a baseline for improvements targeted for the 2026 tournament cycle.

## 1. Tournament Format
The system currently operates on a **Double Elimination** bracket structure, consisting of:
*   **Upper Bracket (Winners)**: Initial placement for all participants.
*   **Lower Bracket (Losers)**: A secondary chance for players who lose in the Upper Bracket.
*   **Grand Finals**: A climactic match between the Upper and Lower bracket winners.
*   **Bracket Reset**: A built-in mechanism where the Lower Bracket winner must win two consecutive matches to win the tournament if they win the first Grand Final match.

## 2. Seeding Logic
Seeding is handled automatically via a **Snake Seeding** algorithm:
*   **Primary Weight**: Qualifier placement (if provided).
*   **Secondary Weight**: osu! Performance Points (PP) for tie-breaking or initial seeding.
*   **Padding**: Automatic inclusion of "BYE" matches to reach the nearest power-of-two participant count (e.g., 8, 16, 32).

## 3. Mappool System
The current implementation utilizes a **User-Submitted Mappool** model:
*   Each player submits their own individual mappool.
*   The system fetches detailed beatmap metadata (Star Rating, BPM, CS, AR, etc.) via the osu! API during the upload phase.
*   Match interfaces allow players to see their own and their opponent's selected maps, facilitating a unique "personalized pool" head-to-head dynamic.

## 4. Technical Architecture
*   **Backend Framework**: Flask (Python) with a modular service-oriented intent (though currently suffering from monolithic tendencies).
*   **Data Storage**: JSON-based file persistence (`tournament.json`).
*   **State Management**: Real-time HTTP polling systems provide updates to the streaming overlay.
*   **Authentication**: OAuth 2.0 integration with the osu! API for player profiles and match results.
*   **Streaming Overlay**: A 1920x1080 fixed-dimension frontend with dedicated states for intro, bracket overview, match interface, and victory screens.

## 5. Identified Challenges for 2026
While functional, the current structure faces several scalability and maintainability hurtles:
*   **Data Integrity**: File-based storage lacks atomic operations, creating risks for data corruption during concurrent writes.
*   **Logic Coupling**: Bracket progression logic is heavily coupled with file I/O, making it difficult to implement new formats (like Swiss or Round Robin).
*   **User Interface**: The monolithic template architecture makes UI updates cumbersome and prevents modern frontend optimizations.
*   **Permission Management**: Legacy admin systems rely on hardcoded IDs rather than a granular, database-backed role system.

---
*Created for the 2026 Tournament Improvement Initiative.*
