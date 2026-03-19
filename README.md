# Thai Lottery Processing System — Automated Lottery Data Pipeline

## Overview
A script-based data processing system designed to automate the collection and publishing of lottery results from multiple independent sources.

## Execution Model
Each data source operates as an independent script with its own execution schedule.  
System execution is coordinated using task scheduling, allowing different workflows to run based on their respective timing requirements.

## Design Context
This project was developed early in my experience as a developer, before formal knowledge of modular architecture and system design patterns.

As a result, each component was implemented independently, leading to a script-based structure optimized for solving immediate operational needs rather than long-term scalability.

## Limitations
- Tight coupling between data collection, processing, and execution logic
- No shared abstraction across different data sources
- Difficult to maintain and extend as the number of sources grows
- Scheduling and orchestration handled externally rather than within the system

## Current Status
This project is being redesigned into a modular and scalable architecture with centralized orchestration and reusable components.