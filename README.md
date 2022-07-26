# createRulesetModelDescription

[![Test/Package Status](https://img.shields.io/github/workflow/status/JasonGlazer/createRulesetModelDescription/Flake8/main?label=flake8)](https://github.com/JasonGlazer/createRulesetModelDescription/actions/workflows/flake8.yml)
[![Build Package and Run Tests](https://github.com/JasonGlazer/createRulesetModelDescription/actions/workflows/build_and_test.yml/badge.svg?branch=main)](https://github.com/JasonGlazer/createRulesetModelDescription/actions/workflows/build_and_test.yml)

An EnergyPlus utility that creates an Ruleset Model Description (RMD) file based on output (and some input) from a simulation. 

## Background

The RMD file is based on a schema being developed as part of the writing of ASHRAE Standard 229P:

Title:

 - Protocols for Evaluating Ruleset Implementation in Building Performance Modeling Software

Purpose:

 - This standard establishes tests and acceptance criteria for implementation of rulesets (e.g., modeling rules) and related reporting in building performance modeling software.

Scope:

 - This standard applies to building performance modeling software that implements rulesets.
 - This standard applies to rulesets associated with new or existing buildings and their systems, system controls, their sites, and other aspects of buildings described by the ruleset implementation being evaluated.

The development of the RMD schema to support the standard is going on here:

https://github.com/open229/ruleset-model-description-schema

## Overview

The utility is intended to be used at a command line prompt:

  createRulesetModelDescription in.epJSON

where in.epJSON is the name of the EnergyPlus input file with path in the epJSON format. EnergyPlus version 22.2.0 or newer is requried to use the utility.

To create an epJSON file from an EnergyPlus IDF file use ConvertInputFormat.exe that comes with EnergyPlus. For help with ConvertInputFormat use the --help option.

The EnergyPlus input file has some added requirements to be used with the createRulesetModelDescription utility.

 - many tabular output reports are used so the Output:Table:SummaryReports should be set to AllSummaryMonthly or AllSummaryMonthlyAndSizingPeriod:

``` 
  Output:Table:SummaryReports,
    AllSummaryMonthly;    !- Report 1 Name
``` 

 - the JSON output format is used so that should be enabled for both timeseries and tabular output:

```    
  Output:JSON,
    TimeSeriesAndTabular,    !- Option Type
    Yes,                     !- Output JSON
    No,                      !- Output CBOR
    No;                      !- Output MessagePack
```
 - SI units should be used so

``` 
   OutputControl:Table:Style,
    HTML,            !- Column Separator
    None;            !- Unit Conversion
```
 - hourly output for each schedule needs to be created using the following
 
```
   Output:Variable,
    *,
    schedule value,
    hourly;
```

It maybe easier to make these changes prior to converting the file into the epJSON format.

The resulting file will be created in the same directory as the epJSON file with the same name and the file extension .rmd




