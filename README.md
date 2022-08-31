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

```
  createRulesetModelDescription in.epJSON
```

where in.epJSON is the name of the EnergyPlus input file with path in the epJSON format. 

EnergyPlus version 22.2.0 or newer is requried to use the utility.

## epJSON Format

To create an epJSON file from an EnergyPlus IDF file use ConvertInputFormat.exe that comes with EnergyPlus. 

To convert files, at the command prompt type:

```
 ConvertInputFormat in.idf
```

Where in.idf is the name of the EnergyPlus input file with path in the IDF format. The utility will convert the file into a file with the same name
but the extension .epJSON in the JSON format. 

For additional help with ConvertInputFormat at the command prompt in the directory with the EnergyPlus application, type:

```
 ConvertInputFormat --help
```

## Required Input File Changes

The EnergyPlus input file has some added requirements to be used with the createRulesetModelDescription utility.

 - many tabular output reports are used so the Output:Table:SummaryReports should be set to AllSummary, AllSummaryMonthly, or AllSummaryMonthlyAndSizingPeriod:

``` 
  Output:Table:SummaryReports,
    AllSummaryMonthly;    !- Report 1 Name
``` 

Additional warning messages may appear when including the monthly predefined reports.

 - the JSON output format is used so that should be enabled for both timeseries and tabular output:

```    
  Output:JSON,
    TimeSeriesAndTabular,    !- Option Type
    Yes,                     !- Output JSON
    No,                      !- Output CBOR
    No;                      !- Output MessagePack
```

This will create filename_out.json files when EnergyPlus is run at the command line. 

Note: This utility was designed to work with files produced using EnergyPlus at the command line. Some file renaming might be necessary if using EP-Launch. 
If using EP-Launch the eplusout.json and eplusout_hourly.json files may be found in the EPTEMP directory without the specific file name.

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

This will create filenameout_hourly.json files when EnergyPlus is run at the command line. If using EP-Launch this files may be found in the EPTEMP directory without the specific file name.

 - add output schedules reports
 
```
  Output:Schedules,
    Hourly;
```

This produces a summary report in the EIO file and the Initialization Summary related to schedules. While it is not currently used by the script it probably will be used 
in the future.


 - add space type tags by using the Space input object

```
  Space,
    core_space,              !- Name
    Core_ZN,                 !- Zone Name
    autocalculate,           !- Ceiling Height
    autocalculate,           !- Volume
    autocalculate,           !- Floor Area {m2}
    OFFICE_OPEN_PLAN,        !- Space Type
    OFFICE_BUILDINGS_OFFICE_SPACE, !- Tag 1
    OFFICE;                  !- Tag 2
```

The fields should be completed as described below:

 - the Space Type field should be set to the appropriate option for lighting_space_type see LightingSpaceOptions2019ASHRAE901TG37 for the list of options.
 - the Tag 1 field should be set to the the appropriate option for ventilations_space_type see VentilationSpaceOptions2019ASHRAE901 for the list of options.
 - the Tag 2 field should be set to the the appropriate option for service_water_heating_space_type see ServiceWaterHeatingSpaceOptions2019ASHRAE901 for the list of options.

These enumerated lists are found here:

https://github.com/open229/ruleset-model-description-schema/blob/master/docs229/Enumerations2019ASHRAE901.schema.md

If you had not been using the Space input object before, set the numeric inputs to 'autocalculate'.

It is usually easier to make these changes prior to converting the file into the epJSON format.

## Weather File

When selecting the EPW weather file, make sure the STAT file is present in the same directory. This file is needed for the fully populate the Climatic Data Summary tabular 
report which is used to identify the ASHRAE climate zone.

## Output

The resulting Ruleset Model Description file will be created in the same directory as the epJSON file with the same name and the file extension .rmd




