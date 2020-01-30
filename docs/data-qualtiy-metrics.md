Data Quality
============

Data Quality metrics are calculated based on the six primary dimensions for data
quality assessment as described in [this document](https://www.dqglobal.com/wp-content/uploads/2013/11/DAMA-UK-DQ-Dimensions-White-Paper-R37.pdf).

On the Knowledge Hub portal, the Data Quality metrics are calculated for each
resource and for each dataset based on the resources it contains.

Data Quality score is calculated for the following dimensions:
* Completeness,
* Uniqueness,
* Timeliness,
* Validity,
* Accuracy, and
* Consistency


The quality score is displayed on the Knowledge Hub portal in the Dataset
info page and per Resource, on the Resource info page, in a separate section
called "Data Quality".

The quality is calculated in a background job, which is scheduled when a new
Dataset or Resource is created, or when the Resources or the Dataset have been
updated. Because for some of the dimensions, the calculation may take some time,
the values may not be available or updated instantaneously, but will become
available once the background job is complete.

These calculations are performed by the system automatically, however you can
override or set the Data Quality values explicitly, using the API exposed on the
portal. When the values for a particular dimension for dataset or resource have
been set explitictly (manually), then that value will be used by the portal and
automatic value will not be calculated.

# Content
- [Data Quality dimensions](#data-quality-dimensions)
  * [Completeness](#completeness)
  * [Uniqueness](#uniqueness)
  * [Timeliness](#timeliness)
    + [Configuring the timeliness settings for automatic calculation](#configuring-the-timeliness-settings-for-automatic-calculation)
    + [Calculation](#calculation)
  * [Validity](#validity)
    + [Configuring the validit](#configuring-the-validit)
  * [Accuracy](#accuracy)
    + [Configuring the accuracy settings](#configuring-the-accuracy-settings)
  * [Consistency](#consistency)
- [API for Data Quality metrics](#api-for-data-quality-metrics)
  * [Get Data Quality metrics](#get-data-quality-metrics)
    + [Get Data Quality for Package](#get-data-quality-for-package)
    + [Get Data Quality for Resource](#get-data-quality-for-resource)
  * [Update Data Quality metrics](#update-data-quality-metrics)
    + [Update Data Quality for Package](#update-data-quality-for-package)
    + [Update Data Quality for Resource](#update-data-quality-for-resource)

# Data Quality dimensions

Data Quality metrics are calculted for each dimension in two phases:

1. In the first phase, the metrics are calculated for each resource in a
particular dataset. This operation is performed on the full resource data and
usualy all of the records of the resource data have to be scanned to calculate
the value. This phase generates a results, in form of a dictionary (JSON object)
that is later used in the seconds phase to calculate the values for the whole
dataset.

The resulting report will always contain at least one property called `value`,
which contains the actual value calculated for the whole data of that resource.

Different dimensions may add additional properties in which they store the
results, like:
 * `total` - total number of checked values or records
 * `unique` - number of unique values (for Uniqueness)
 * `complete` - number of columns that are completed and contain value (for 
 Completeness)

and many others. Details on which properties are populated are descibed in the
sections bellow where each dimension is described in details.

2. The second phase calculates the cumulative/aggregate value of the dimension
metric, for all resources. It reuses the results produced in the first phase - 
this works much like a map-reduce algorithm, where in the map phase we calculate
the values for each resource in a dataset, and then in the reduce phase we reduce
those results in a single result for the whole dataset.

The results for each individual resource, and the results for the whole dataset
are then stored in database. Historical results are also kept in database, when
the data chnages, new record is stored in the database with the latest values
for Data Quality dimensions, and the old one is kept. This offers a way to do a
historical analysis on how the Data Quality evolves over time with the updates
on the data.

The actual records for Data Quality (both for Dataset and Resource) have the
following JSON structure:

```javascript
{
    "calculated_on": "2020-01-27T21:30:37.091640",  // ISO-8601 date string
    "accuracy": 74.92682926829268, // floating point number
    "completeness": 100.0,         // floating point number
    "consistency": 100.0,          // floating point number
    "timeliness": "+2382 days, 5:57:23",   // time delta string
    "package_id": "31544672-5807-44fa-aabb-9a0b1423e69d",  // for dataset only
    "resource_id": "3f7879ed-1f36-40de-b577-7b3029fccad3",  // for resource only
    "uniqueness": 27.790940766550523, // floating point number
    "validity": 100.0,             // floating point number
    "details": {
        "completeness": {
        "total": 21525,
        "complete": 21525,
        "value": 100.0
      },
      "timeliness": {
        "records": 3075,
        "average": 205826243,
        "total": 632915698297,
        "value": "+2382 days, 5:57:23"
      },
      "validity": {
        "total": 3075,
        "valid": 3075,
        "value": 100.0
      },
      "uniqueness": {
        "total": 21525,
        "unique": 5982,
        "value": 27.790940766550523
      },
      "consistency": {
        "consistent": 21525,
        "total": 21525,
        "value": 100.0
      },
      "accuracy": {
        "accurate": 2304,
        "total": 3075,
        "inaccurate": 771,
        "value": 74.92682926829268
      }
    }

}
```
Note that the details for resource Data Quality may have even more additional
values when automatic calculation have been performed.

## Completeness

This metric tells the proportion of stored data against the potential of
"100% complete".

For a given resource data, we calculate the number of all cells (in a tabular
data) and the number of cells that have value. Then the calculation is perfomed
to get the ratio of cells with value over the total number of cells as 
a percentage.

For each resource we calculate:
* `total` - total number of values (cells). This is basically number of rows
    in the data multiplied by the number of columns.
* `complete` - number of cells that acutally contain value.
* `value` - the ratio `complete/total` expressed as a percentage (0-100)

To obtain the value for a dataset, we use the calculations for each resource,
and the calculate the following:
* `total` - total number of cells in all resources. Sum of all `total` values 
    for each resource.
* `complete` - the total number of cells that have value. Sum of all `complete`
    values for each resource in the dataset.
* `value` - the ratio `complete/total` as percentage.

### Example



Given the data for a resouce:

| col1 | col2 | col3 |
|------|------|------|
| 1    |      |      |
| 2    | 3    | 4    |
| 5    | 6    |      |
| 7    |      | 8    |

There are 8 values, and a total of 12 cells. So the completeness score would be 
`8/12 * 100 = 66.6667%`

## Uniqueness

Uniqueness is analysis of the number of things as assessed in the 'real world' compared to the number of records of things in the data set. The real world number of things could be either determined from a different and perhaps more reliable data set or a relevant external comparator.

In th Knowledge Hub, the measure of uniqueness is the percentage
of unique values present in the data. For a specific resource it
counts the number of unique values per column, then counts the total number of values present in the data.

Given a tabular data in a resource, we count the number of values for that column and count how many of those are distinct values.
Then, the calculation to obtain the percentage of unique values
is done by taking the sum of all unique value for all columns, then expressing that as a percentage of the sum of all values
in the data.
The result of the calculation per resource contains the follwing values:
* `total` - total number of values in the data (from all columns)
* `unique` - number of unique values (from all columns)
* `value` - ratio `unique/total` expressed as percentage (0-100%)
* `columns` - full report per column for the calculated values.

For a dataset, we use the previously calculated values from the resources and calculate the following:
* `total` - total number of values in the data (from all resource)
* `unique` - number of unique values (from all resources)
* `value` - ratio `unique/total` expressed as percentage (0-100%)

### Example:

Given the data for a resouce:

| col1     | col2    | col3    |
|------    |------   |------   |
| 1        | 3       | 4       |
| 2        | 3       | 4       |
| 5        | 6       | 4       |
| 7        | 6       | 8       |
|-         |-        |-        |
|total: 4  |total: 4 |total: 4 |
|unique: 4 |unique: 2|unique: 2|

Then to calculate the final value we do: 
* Calculate `total` (for all columns) = `4 + 4 + 4 = 12`
* Calculate `unique` (for all columns) = `4 + 2 + 2 = 8`
* Final value is `unique/total * 100 = 8/12 * 200 = 66.6667%`

## Timeliness

Timeliness represents a metric on how much delay is there between the time a measurement have been taken and the time it was recored in the system. It given an estimation on the degree to whichdata represent reality from the required point in time.

To calculate the timeliness of the data, we must first know the
time that record (measurement) has been taken. The time it has entered the Knowledge Hub is known by the `last_modified` timestamp - the timestamp when the data was imported to the hub.

The date of taking the measurement can be put anywhere in the records columns, so this must be configured manually, on a resource level.

### Configuring the timeliness settings for automatic calculation

The timeliness needs two configuration settings to do the calculation manually:
* `column` - the name of the column that contains the record of the time the measurement has been taken, and
* `date_format` - _(optional)_, the format of the date/time in the column. This is optional, and if not specified the system will try to guess and parse the time anyway.

The `column` setting must be specified, and if not specified, then the system will **not** attempt to calculate the timeliness metric.

To configure this, on the Resource Create page, or Resource Update page, go to *Data Quality Settings* -> *Timeliness* section.
Two fields are available:
* Column - the name of the column in the data that contains the time, and
* Date Format - the date/time format, in python `strptime` format.


On a resource level, the following configuration is expected by the system:

```javascript
// resource data in JSON
{
    "id": "resource-id",
    ... // other resource fields
    "data_quality_settings": {
        "timeliness": {
            "column": "<column>",
            "format": "<strptime format, like '%Y-%m-%d'>"
        }
    }
}   
```

Keep in mind that these settings are kept in CKAN resources in `extras`.

### Calculation

The system will calculate the time delta between the `last_modified` and the date in the timeliness column. Total delta expressed in seconds will be obtained. Then, this value i divided by the number of checked records to obtain an average delay in seconds.
The value then is converted to string, human readable time delay that is presented to the user.

Calculated values are:
* `total` - total delay in seconds for all records.
* `average` - average delay in seconds.
* `records` - total number of checked records.
* `value` - time delta, in human readable representation.

### Example

Given the data:

| col1 | col2 | recorded_at                |
|---   |---   |---                         |
| 1    | val  | 2020-01-20T15:36:16 |
| 2    | val2 | 2020-01-21T15:36:16 |
| 3    | val3 | 2020-01-22T15:36:16 |
| 4    | val4 | 2020-01-23T15:36:16 |

Let's assume that the `last_modified` timestamp (the time of entry in the hub) is `2020-01-30T15:36:16`, then we can calculate the total time delta in seconds:

```
2020-01-30T15:36:16 - 2020-01-20T15:36:16 = 864000
2020-01-30T15:36:16 - 2020-01-21T15:36:16 = 777600
2020-01-30T15:36:16 - 2020-01-22T15:36:16 = 691200
2020-01-30T15:36:16 - 2020-01-23T15:36:16 = 604800
--------------------------------------------------
                                    total: 2937600
```

Then to get the average delay, we divide the total by 4 (4 records):
2937600/4 = 734400

The values would be: 
* `total` = 2937600
* `average` = 734400
* `records` = 4
* `value` = **'8 days, 12:00:00'** - human readable time delta

## Validity

Validity measures the percentage of valid records in the data.
The validity is determined by using a schema for the data.
The schema and validation functionality is provided by the library [goodtables](https://github.com/frictionlessdata/goodtables-py).

The value for this metric is calculated per resource and dataset.
For each resource, we validate the full data of that resource.
We count the number of valid records and total number of records. Then we represent the number of valid records as a percentage of the total records.

For dataset, we sum up the total number of records and the total number of valid records for each resource and calculate the ration as a percentage.

This metric produces report with the following values:
* `total` - total number of records.
* `valid` - number of valid records.
* `value` - ratio `valid/total` as percentage (0-100%).

### Configuring the validit

To configure and run the automatic validity calculation, you must set the data schema.
This is set up in *Resource Update*/*Resource Create* page, in the *Schema* field.

The schema is a `JSON` document that describes the data.
An examle of a schema document:
```json
{
    "primaryKey": "id",
    "fields": [
        {
            "name": "id",
            "title": "Measurement identifier",
            "type": "integer"
        },
        {
            "name": "location",
            "title": "Measurement location code",
            "type": "string",
            "constraints": {
                "enum": ["A", "B", "C", "D"]
            }
        },
        {
            "name": "date",
            "title": "Measurement date",
            "type": "date",
            "format": "%d/%m/%Y"
        },
        {
            "name": "measurement",
            "title": "Measure of the oblique fractal impedance at noon",
            "type": "number",
            "constraints": {
                "required": true
            }
        },
        {
            "name": "observations",
            "title": "Extra observations",
            "type": "string"
        }
    ]
}
```

More can be read on the [goodtables site](https://github.com/frictionlessdata/goodtables-py).


### Example

Given this data:
| col1 | col2 |
|------|------|
| val0 | 10   |
| val1 | test |
| val2 | 10   |
| val3 |      |

And the following schema:

```json
{
    "fields": [{
        "name": "col1",
        "type": "string"
    }, {
        "name": "col2",
        "type": "integer"
    }]
}
```
We expect to have a string value in `col1` and integer value for `col2`. However, we can see in the second and the last row we don't have a valid integer value (`"test"` and empty value in the last). So only 2 of the 4 records are valid.
This will yield this report:
```json
{
    "total": 4,
    "valid": 2,
    "value": 50.0
}
```

## Accuracy

Accuracy represents the degree to whichdata correctly describes the "real world" object or event being described.

To determine if a record is accurate or not, a background research must be performed. This is not an automatic process as depends a lot of the data in hand (references to other datasets and primary research done by humans).

However, the system offers a basic calculation a measurement based on a previous research and the results of which are kept in the data itself.

If a primary research have been performed, and the results of which are present in the data itself - separate column having a value that flags the record as accurate, inaccurate or none, then the system can calculate the percentage of accuracy automatically.

The result of the calculation is a report containing the following values:
* `accurate` - number of records marked as accurate.
* `inaccurate` - number of records marked as inaccurate
* `total` - total number of checked records, basically `total = accurate + inaccurate`
* `value` - percentage of accurate values: `accurate/total * 100`

### Configuring the accuracy settings

The accuracy column must be configured by resource.
In the *Resource Create*/*Resource Update* page, scroll down to
*Data Quality Settings* section, in *Accuracy* you can enter the name of the column that contains the flags for the accuracy of the records.
The system recognizes the following values to mark a record as accurate: `T`, `true`, `1`, `Yes` (case insensitive).
If a value is given and is not in the values above, the record is considered as inaccurate.
If no value is set, then the records not counted as accurate or inaccurate, basically the accuracy of the record is not determined.

### Example

Given the data bellow:

| col1 | is_accurate |
|---   |---          |
| val  | T           |
| val  | F           |
| val  | F           |
| val  | T           |
| val  | T           |
| val  |             |
| val  |             |
| val  |             |
| val  | T           |
| val  |             |

Assuming the name of the column is set to `is_accurate`, there
are 4 records that are accurate (marked with `T`) and 2 records
marked as inaccurate (with `F`). The rest of the records are not
taken into account when calculating the accuracy.

This would yield the following report:

```json
{
    "total": 6,
    "accurate": 4,
    "inaccurate": 2,
    "value": 66.666666,
}
```

## Consistency

Consistency measures the absence of difference, when comparing two or more representations of a thing against a definition.

The metric basically measures if the values for the same types of data - like numbers, strings, dates etc, do look the same. For example, this metric will calculate the number of date-time values that use the same format across a resource and dataset.

The system provides automatic check for some types of values, which can be determined in a generic way - like date string format and numeric values (same format for integers or decimal values).

The metric is calculated per resource data, where based on the type of each column, the system will try to determine the format of the value used. The number of values that are automatically recognized is counted, excluding the values for which we cannot determine the format or type.

This generates a report, by column, containing multiple categories of values, one for each type of format used, and a count of values belonging to that group.

The value for the resource is calculated as an aggregated percentage of the report by column, taking into consideration only the group with highest number of values, taking that as the baseline format for the values in that column.

The calculation result report contains the follosing values:
* `total` - total number of checked values (excluding the values for which we cannot determine the consistency)
* `consistent` - total number of consistent values (across columns)
* `value` - the percentage of consistent values - `consistent/total * 100`
* `report` - a detailed report for each column. An example:
```json
"report": {
    "status": {
        "count": 3075,
        "consistent": 3075,
        "formats": {
            "text": 3075
        }
    },
    "date": {
        "count": 3075,
        "consistent": 3075,
        "formats": {
            "%Y-%m-%dT%H:%M:%S": 3075
        }
    }
}
```

### Example

Given the data bellow, that contains multiple types of formats:

| col1      | col2      | col3                    |
|---        |---        |---                      |
| value1    | 10000     | 2020-10-10              |
| value2    | 10,000    | 2020-10-10              |
| value3    | 12345     | 2020-10-10              |
| value4    | 112,123   | 2020-10-10              |
| value5    | 30000     | 2020-10-10              |
| value6    | 40000     | 2020-10-10              |
| value7    | 40000     | 2020-10-10              |
| value8    | 50000     | 2020-10-10T11:12:13     |
| value9    | 10,000    | 2020-10-10T12:12:13     |
| value10   | 11,000    | 2020-10-10T13:12:13     |
| value11   | 12,000    | 2020-10-10T14:12:13     |
| value12   | 13,000    | 2020-10-10T15:12:13     |
| value13   | 14,000    | 2020-10-10T16:12:13     |
| value14   | 15,000    | 2020-10-10T17:12:13     |
| value15   | 16,000    | 2020-10-10T18:12:13     |

Lets assume the type of the columns:
* col1 - `text`
* col2 - `numeric`
* col3 - `timestamp`

There are 15 records. For each column:
* `col` - 15 records that are text and consistent: `total: 15, consistent: 15`,
* `col2` - 15 records, 5 with standard integer format and 10 with comma separator for the thousands
* `col3` - 15 records, 7 containing only year, month and day; 8 containing information about the time as well.

The column report would look like this:
```json
{
    "col1": {
        "count": 15,
        "consistent": 15,
        "formats": {
            "text": 15
        }
    },
    "col2": {
        "count": 15,
        "consistent": 10,
        "formats": {
            "int": 5,
            "^(\\d{1,3},)+(\\d{3})$": 10
        }
    },
    "col3": {
        "count": 15,
        "consistent": 8,
        "formats": {
            "%Y-%m-%d": 7,
            "%Y-%m-%dT%H:%M:%S": 8
        }
    }
}
```

Note that in the cases where we have multiple formats, we take the number of consistent values to be highest number of values in that group.

The total value is the calculated:
* `total` - `15+15+15`, which is `45`
* `consistent` - `15` (col1) + `10` (col2) + `8` (col3), which is 33
* `value` - percentage of `consistent` over `total`, which is `33/45 * 100` equals to `73.3%`


# API for Data Quality metrics

The system exposes an API for retrieval of the Data Quality metrics data, and also for setting the values of the dimensions manually.

There are two types of actions exposed:
* GET actions - these actions retrieve the Data Quality values for a particular dataset or resource. Thee actions do not change the data.
* UPDATE actions - these actions update or set the Data Quality values for a particular dataset or resoruce.

You can set all of the data quality metrics for a dataset/resource or you can just set the values for some of the dimensions. The system treats the update as a patching action, and if the value for a particular dimension is not set in the request data, it will keep the old value unchanged.

Once you have updated/set the value for a particular dimension, that value is marked as `manual`, and will not be recalculated automatically when the data changes.

## Get Data Quality metrics

There are two actions to fetch the data quality values:
1. Fetch the Data Quality for a dataset (package in CKAN terminologu), and
2. Fetch the Data Quality for a resource

### Get Data Quality for Package

Fetches the data quality values for a particular dataset

* Path: `/api/3/action/package_data_quality`
* Method: `GET`
* Params:
    * `id` - the ID of the package
* Response:
    * Type `JSON`
    * Response object:
    ```json
    {
        "help": "http://localhost:5000/api/3/action/help_show?name=package_data_quality",
        "success": true,
        "result": {
        "completeness": 100.0,
        "calculated_on": "2020-01-27T21:30:37.091640",
        "timeliness": "+2382 days, 5:57:23",
        "package_id": "31544672-5807-44fa-aabb-9a0b1423e69d",
        "validity": 100.0,
        "uniqueness": 27.7909407665505,
        "details": {
            "completeness": {
            "total": 21525,
            "complete": 21525,
            "value": 100.0
            },
            "timeliness": {
            "records": 3075,
            "average": 205826243,
            "total": 632915698297,
            "value": "+2382 days, 5:57:23"
            },
            "validity": {
            "total": 3075,
            "valid": 3075,
            "value": 100.0
            },
            "uniqueness": {
            "total": 21525,
            "unique": 5982,
            "value": 27.790940766550523
            },
            "consistency": {
            "consistent": 21525,
            "total": 21525,
            "value": 100.0
            },
            "accuracy": {
            "accurate": 2304,
            "total": 3075,
            "inaccurate": 771,
            "value": 74.92682926829268
            }
        },
        "consistency": 100.0,
        "accuracy": 74.9268292682927
        }
    }
    ```

Example:
```bash
curl -H "Authorization: $API_KEY" \
     "$KNOWLEDGE_HUB_HOST/api/3/action/package_data_quality?id=31544672-5807-44fa-aabb-9a0b1423e69d"
```

Response:
```json
{
  "help": "http://localhost:5000/api/3/action/help_show?name=package_data_quality",
  "success": true,
  "result": {
    "completeness": 100.0,
    "calculated_on": "2020-01-27T21:30:37.091640",
    "timeliness": "+2382 days, 5:57:23",
    "package_id": "31544672-5807-44fa-aabb-9a0b1423e69d",
    "validity": 100.0,
    "uniqueness": 27.7909407665505,
    "details": {
      "completeness": {
        "total": 21525,
        "complete": 21525,
        "value": 100.0
      },
      "timeliness": {
        "records": 3075,
        "average": 205826243,
        "total": 632915698297,
        "value": "+2382 days, 5:57:23"
      },
      "validity": {
        "total": 3075,
        "valid": 3075,
        "value": 100.0
      },
      "uniqueness": {
        "total": 21525,
        "unique": 5982,
        "value": 27.790940766550523
      },
      "consistency": {
        "consistent": 21525,
        "total": 21525,
        "value": 100.0
      },
      "accuracy": {
        "accurate": 2304,
        "total": 3075,
        "inaccurate": 771,
        "value": 74.92682926829268
      }
    },
    "consistency": 100.0,
    "accuracy": 74.9268292682927
  }
}
```

### Get Data Quality for Resource

Fetches the data quality values for a particular resource.

* Path: `/api/3/action/resource_data_quality`
* Method: `GET`
* Params:
    * `id` - the ID of the resource
* Response:
    * Type `JSON`
    * Response object:
    ```javascript
    {
      "help": "http://localhost:5000/api/3/action/help_show?name=resource_data_quality",
      "success": true,
      "result": {
        "completeness": 78.8,
        "resource_id": "3f7879ed-1f36-40de-b577-7b3029fccad3",
        "calculated_on": "2020-01-28T19:34:15.044138",
        "timeliness": "+2382 days, 5:57:23",
        "validity": 100.0,
        "uniqueness": 27.7909407665505,
        "details": {
          "completeness": {
            "total": 21525,
            "complete": 21525,
            "value": 100.0
          },
          "timeliness": {
            "records": 3075,
            "average": 205826243.0,
            "total": 632915698297,
            "value": "+2382 days, 5:57:23"
          },
          "validity": {
            "total": 3075,
            "valid": 3075,
            "value": 100.0
          },
          "uniqueness": {
            "total": 21525,
            "unique": 5982,
            "columns": {
              "status": {
                "total": 3075,
                "unique": 2,
                "value": 0.06504065040650407
              },
              ... // other columns details
            },
            "value": 27.790940766550523
          },
          "consistency": {
            "report": {
              "status": {
                "count": 3075,
                "consistent": 3075,
                "formats": {
                  "text": 3075
                }
              },
              ... // other columns details
            },
            "consistent": 21525,
            "total": 21525,
            "value": 100.0
          },
          "accuracy": {
            "accurate": 2304,
            "total": 3075,
            "inaccurate": 771,
            "value": 74.92682926829268
          }
        },
        "consistency": 100.0,
        "accuracy": 74.9268292682927
      }
    }
    ```

Example:
```bash
curl -H "Authorization: $API_KEY" \
     "$KNOWLEDGE_HUB_HOST/api/3/action/resource_data_quality?id=3f7879ed-1f36-40de-b577-7b3029fccad3"
```

Response:
```json
{
      "help": "http://localhost:5000/api/3/action/help_show?name=resource_data_quality",
      "success": true,
      "result": {
        "completeness": 78.8,
        "resource_id": "3f7879ed-1f36-40de-b577-7b3029fccad3",
        "calculated_on": "2020-01-28T19:34:15.044138",
        "timeliness": "+2382 days, 5:57:23",
        "validity": 100.0,
        "uniqueness": 27.7909407665505,
        "details": {
          "completeness": {
            "total": 21525,
            "complete": 21525,
            "value": 100.0
          },
          "timeliness": {
            "records": 3075,
            "average": 205826243.0,
            "total": 632915698297,
            "value": "+2382 days, 5:57:23"
          },
          "validity": {
            "total": 3075,
            "valid": 3075,
            "value": 100.0
          },
          "uniqueness": {
            "total": 21525,
            "unique": 5982,
            "columns": {
              "status": {
                "total": 3075,
                "unique": 2,
                "value": 0.06504065040650407
              },
              "age": {
                "total": 3075,
                "unique": 25,
                "value": 0.8130081300813008
              },
              "period": {
                "total": 3075,
                "unique": 41,
                "value": 1.3333333333333333
              },
              "sex": {
                "total": 3075,
                "unique": 3,
                "value": 0.0975609756097561
              },
              "_id": {
                "total": 3075,
                "unique": 3075,
                "value": 100.0
              },
              "accurate": {
                "total": 3075,
                "unique": 2,
                "value": 0.06504065040650407
              },
              "population": {
                "total": 3075,
                "unique": 2834,
                "value": 92.16260162601625
              }
            },
            "value": 27.790940766550523
          },
          "consistency": {
            "report": {
              "status": {
                "count": 3075,
                "consistent": 3075,
                "formats": {
                  "text": 3075
                }
              },
              "age": {
                "count": 3075,
                "consistent": 3075,
                "formats": {
                  "text": 3075
                }
              },
              "period": {
                "count": 3075,
                "consistent": 3075,
                "formats": {
                  "%Y-%m-%dT%H:%M:%S": 3075
                }
              },
              "sex": {
                "count": 3075,
                "consistent": 3075,
                "formats": {
                  "text": 3075
                }
              },
              "_id": {
                "count": 3075,
                "consistent": 3075,
                "formats": {
                  "int": 3075
                }
              },
              "accurate": {
                "count": 3075,
                "consistent": 3075,
                "formats": {
                  "text": 3075
                }
              },
              "population": {
                "count": 3075,
                "consistent": 3075,
                "formats": {
                  "int": 3075
                }
              }
            },
            "consistent": 21525,
            "total": 21525,
            "value": 100.0
          },
          "accuracy": {
            "accurate": 2304,
            "total": 3075,
            "inaccurate": 771,
            "value": 74.92682926829268
          }
        },
        "consistency": 100.0,
        "accuracy": 74.9268292682927
      }
    }
```

### Update Data Quality metrics

These actions update (patch) the data quality values for all or a subset of the dimensions.

It is important to note that once the value have been updated via the API, the system will treat that value as an authority and will not update the value automatically.

There are two actions to update the Data Quality metrics:
1. Update Data Quality values for a particular dataset (package), and
2. Update Data Quality values for a particular resource.

### Update Data Quality for Package

Updates all or a subset of a data quality values for a particular dataset. If no calculation have been performed, it will insert these values for the dataset.

* Path: `/api/3/action/package_data_quality_update`
* Method: `POST`
* Request:
    * `JSON` object of the following structure:
    ```javascript
    {
        "id": "<the id of the package>",
        "<metric-name>": { // the name of the metric, like: completeness, uniqueness etc
            "value": 10.0,  // the value of the metric score - must be present
            "total": 1000,  // optional additional values
            "complete": 10  // optional additional values
        },
        "<another-metric": {
            ...  // another metric to update
        }
    }
    ```
* Reponse:
    * `JSON` object:
    * The format is the same as the GET actions

### Examples

Update a metric:

```bash
curl -H "Authorization: $API_KEY" \
    -X POST \
    "$KNOWLEDGE_HUB_HOST/api/3/action/resource_data_quality" \
    -d '{
        "id": "31544672-5807-44fa-aabb-9a0b1423e69d",
        "completeness": {
            "value": 83.8,
            "total": 1000,
            "complete": 838
        }
    }'
```

The result:
```javascript
{
  "help": "http://localhost:5000/api/3/action/help_show?name=package_data_quality_update",
  "success": true,
  "result": {
    "completeness": 83.8,  // this was updated
    "timeliness": "+2382 days, 5:57:23",
    "validity": 100.0,
    "uniqueness": 27.7909407665505,
    "calculated_on": "2020-01-26T23:03:22.546213",
    "consistency": 100.0,
    "details": {
      "completeness": {
        "total": 1000,
        "manual": true,  // note that this is now set to 'manual'
        "complete": 838,
        "value": 83.8
      },
      "timeliness": {
        "records": 3075,
        "average": 205826243,
        "total": 632915698297,
        "value": "+2382 days, 5:57:23"
      },
      ...  // other details unchanged
    },
    "accuracy": 74.9268292682927
  }
}
```

## Update Data Quality for Resource

Updates all or a subset of a data quality values for a particular resource. If no calculation have been performed, it will insert these values for the resource.

* Path: `/api/3/action/resource_data_quality_update`
* Method: `POST`
* Request:
    * `JSON` object of the following structure:
    ```javascript
    {
        "id": "<the id of the resource>",
        "<metric-name>": { // the name of the metric, like: completeness, uniqueness etc
            "value": 10.0,  // the value of the metric score - must be present
            "total": 1000,  // optional additional values
            "complete": 10  // optional additional values
        },
        "<another-metric": {
            ...  // another metric to update
        }
    }
    ```
* Reponse:
    * `JSON` object:
    * The format is the same as the GET actions

### Examples

Update a metric:

```bash
curl -H "Authorization: $API_KEY" \
    -X POST \
    "$KNOWLEDGE_HUB_HOST/api/3/action/resource_data_quality" \
    -d '{
        "id": "3f7879ed-1f36-40de-b577-7b3029fccad3",
        "completeness": {
            "value": 78.8,
            "total": 1000,
            "complete": 788
        }
    }'
```

The result:
```javascript
{
  "help": "http://localhost:5000/api/3/action/help_show?name=resource_data_quality_update",
  "success": true,
  "result": {
    "completeness": 78.8,  // updated this value
    "timeliness": "+2382 days, 5:57:23",
    "validity": 100.0,
    "uniqueness": 27.7909407665505,
    "calculated_on": "2020-01-28T19:34:15.044138",
    "consistency": 100.0,
    "details": {
      "completeness": {  // this whole section is now updated
        "total": 1000,
        "manual": true,  // this was set to 'manual'
        "complete": 788,
        "value": 78.8
      },
      "timeliness": {
        "records": 3075,
        "average": 205826243.0,
        "total": 632915698297,
        "value": "+2382 days, 5:57:23"
      },
      "validity": {
        "total": 3075,
        "valid": 3075,
        "value": 100.0
      },
      ... // other dimensions values are unchanged
    },
    "accuracy": 74.9268292682927
  }
```