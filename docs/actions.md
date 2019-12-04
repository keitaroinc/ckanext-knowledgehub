KnowledgeHub 1.0.0 documentation

KnowledgeHub's logic actions
============================


action.create module
--------------------

`corpus_create`(_context_, _data\_dict_)

Store RNN corpus

:param corpus

`dashboard_create`(_context_, _data\_dict_)

Create new dashboard

> :param name :param title :param description :param type :param source :param indicators

`kwh_data_create`(_context_, _data\_dict_)

Store Knowledge Hub data

:param type :param content

`package_create`(_context_, _data\_dict_)

`research_question_create`(_context_, _data\_dict_)

Create new research question.



Parameters:

*   **content** (_string_) – The research question.
*   **theme** – Theme of the research question.
*   **sub\_theme** – SubTheme of the research question.
*   **state** (_string_) – State of the research question. Default is active.

`resource_create`(_context_, _data\_dict_)

Override the existing resource\_create to support data upload from data sources



Parameters:

**db\_type** (_string_) – title of the sub-theme

`` `MSSQL` `` :param host: hostname :type host: string :param port: the port :type port: int :param username: DB username :type username: string :param password: DB password :type password: string :param sql: SQL Query :type sql: string

`` `Validation` `` :param schema: schema to be used for validation :type schema: string :param validation\_options: options to be used for validation :type validation\_options: string

`resource_feedback`(_context_, _data\_dict_)
Resource feedback mechanism

> :param type :param dataset :param resource

`resource_view_create`(_context_, _data\_dict_)

Creates a new resource view.



Parameters:

*   **resource\_id** (_string_) – id of the resource
*   **title** (_string_) – the title of the view
*   **description** (_string_) – a description of the view (optional)
*   **view\_type** (_string_) – type of view
*   **config** (_JSON string_) – options necessary to recreate a view state (optional)

Returns:

the newly created resource view

Return type:

dictionary

`sub_theme_create`(_context_, _data\_dict_)

Creates a new sub-theme



Parameters:

*   **title** (_string_) – title of the sub-theme
*   **name** (_string_) – name of the sub-theme
*   **description** (_string_) – a description of the sub-theme (optional)
*   **theme** (_string_) – the ID of the theme

Returns:

the newly created sub-theme

Return type:

dictionary

`theme_create`(_context_, _data\_dict_)

Create new analytical framework Theme

> :param name :param title :param description

action.delete module
--------------------

`dashboard_delete`(_context_, _data\_dict_)

Deletes existing dashboard by id :param id

`research_question_delete`(_context_, _data\_dict_)

Delete research question.



Parameters:

**id** (_string_) – Research question database id.

`sub_theme_delete`(_context_, _data\_dict_)

Deletes a sub-theme



Parameters:

**id** (_string_) – the sub-theme’s ID

Returns:

OK

Return type:

string

`theme_delete`(_context_, _data\_dict_)

Deletes existing analytical framework Theme by id :param id

action.get module
-----------------

`dashboard_list`(_context_, _data\_dict_)

List dashboards



Parameters:

*   **page** (_integer_) – current page in pagination (optional, default to 1)
*   **sort** (_string_) – sorting of the search results. Optional. Default: “name asc” string of field name and sort-order. The allowed fields are ‘name’, and ‘title’
*   **limit** (_integer_) – Limit the search criteria (defaults to 10000).
*   **offset** (_integer_) – Offset for the search criteria (defaults to 0).

Returns:

a dictionary including total items, page number, items per page and data(dashboards)

Return type:

dictionary

`dashboard_show`(_context_, _data\_dict_)

> Returns existing dashboard



Parameters:

**id** – id of the dashboard that you

want to search against. :type id: string



Parameters:

**name** – name of the dashboard

that you want to search against. (Optional) :type name: string



Returns:

single dashboard dict

Return type:

dictionary

`dashboards_for_rq`(_context_, _data\_dict_)

`get_chart_data`(_context_, _data\_dict_)

Return the resource data from DataStore.



Parameters:

*   **sql\_string** (_string_) – the SQL query that will be executed to get the data.
*   **category** (_string_) – the selected category
*   **x\_axis** (_string_) – the X axis dimension
*   **y\_axis** (_string_) – the Y axis dimension
*   **chart\_type** (_string_) – the type of the chart
*   **resource\_id** (_string_) – the ID of the resource

Return type:

list of dictionaries.

`get_last_rnn_corpus`(_context_, _data\_dict_)

Returns last RNN corpus :returns: a RNN corpus :rtype: string

`get_predictions`(_context_, _data\_dict_)

Returns a list of predictions :param text: the text for which predictions have to be made :type text: string :returns: predictions :rtype: list

`get_resource_data`(_context_, _data\_dict_)

Return the resource data from DataStore.



Parameters:

**sql\_string** (_string_) – the SQL query that will be executed to get the data.

`get_rq_url`(_context_, _data\_dict_)

`knowledgehub_get_geojson_properties`(_context_, _data\_dict_)

`knowledgehub_get_map_data`(_context_, _data\_dict_)

`kwh_data_list`(_context_, _data\_dict_)

List KnowledgeHub data :param type: origin of the data, one of theme, sub-theme,

> rq and search



Parameters:

*   **content** (_string_) – the actual data
*   **user** (_string_) – the user ID
*   **theme** (_string_) – the theme ID
*   **sub\_theme** (_string_) – the sub-theme ID
*   **rq** (_string_) – the research question ID

Returns:

a dictionary including total items, page number, items per page and data(KnowledgeHub data)

Return type:

dictionary

`research_question_list`(_context_, _data\_dict_)

List research questions



Parameters:

**page** – current page in pagination

(optional, default: `1`) :type page: int :param pageSize: the number of items to return (optional, default: `10000`) :type pageSize: int



Returns:

a dictionary including total items, page number, page size and data

Return type:

dictionary

`research_question_show`(_context_, _data\_dict_)

Show a single research question.



Parameters:

**id** (_string_) – Research question database id

Returns:

a research question

Return type:

dictionary

`resource_feedback_list`(_context_, _data\_dict_)

List resource feedbacks



Parameters:

*   **page** (_integer_) – current page in pagination (optional, default to 1)
*   **sort** (_string_) – sorting of the search results. Optional. Default: “name asc” string of field name and sort-order. The allowed fields are ‘name’, and ‘title’
*   **limit** (_integer_) – Limit the search criteria (defaults to 1000000).
*   **offset** (_integer_) – Offset for the search criteria (defaults to 0).
*   **type** – one of the available resource feedbacks(useful, unuseful,

trusted, untrusted). :type type: string :param resource: resource ID :type resource: string :param dataset: dataset ID :type dataset: string



Returns:

a dictionary including total items, page number, items per page and data(feedbacks)

Return type:

dictionary

`resource_user_feedback`(_context_, _data\_dict_)

Returns user’s feedback



Parameters:

**resource** – resource ID

Returns:

a resource feedback as dictionary

Return type:

dictionary

`resource_view_list`(_context_, _data\_dict_)
Return the list of resource views for a particular resource.



Parameters:

**id** (_string_) – the id of the resource

Return type:

list of dictionaries.

`sub_theme_list`(_context_, _data\_dict_)

List sub-themes



Parameters:

*   **page** (_int_) – current page in pagination (optional, default: `1`)
*   **pageSize** – the number of items to

return (optional, default: `10000`) :type pageSize: int



Returns:

a dictionary including total

items, page number, page size and data(sub-themes) :rtype: dictionary

`sub_theme_show`(_context_, _data\_dict_)

Shows a sub-theme



Parameters:

**id** (_string_) – the sub-theme’s ID

:param name the sub-theme’s name :type name: string



Returns:

a sub-theme

Return type:

dictionary

`test_import`(_context_, _data\_dict_)

`theme_list`(_context_, _data\_dict_)

List themes



Parameters:

*   **page** (_integer_) – current page in pagination (optional, default to 1)
*   **sort** (_string_) – sorting of the search results. Optional. Default: “name asc” string of field name and sort-order. The allowed fields are ‘name’, and ‘title’
*   **limit** (_integer_) – Limit the search criteria (defaults to 10000).
*   **offset** (_integer_) – Offset for the search criteria (defaults to 0).

Returns:

a dictionary including total items, page number, items per page and data(themes)

Return type:

dictionary

`theme_show`(_context_, _data\_dict_)

> Returns existing analytical framework Theme



Parameters:

**id** – id of the resource that you

want to search against. :type id: string



Parameters:

**name** – name of the resource

that you want to search against. (Optional) :type name: string



Returns:

single theme dict

Return type:

dictionary

`visualizations_for_rq`(_context_, _data\_dict_)

List visualizations (resource views) based on a research question

Only resource views of type chart, table and map are considered.



Parameters:

**research\_question** (_string_) – Title of a research question

Returns:

list of dictionaries, where each dictionary is a resource view

Return type:

list


`search_dashboards`(_context_, _data\_dict_)

Does a search for dashboard in the Solr index.

**Parameters:**

* `text` - `str`, _required_, the text to search for.
* `rows` - `int`, _optional_, number of rows to return.
* `start` - `int`, _optional_, offset, start from this result then return `rows`
            results.
* `fq` - `string`/`list`, _optional_, additional filter queries as specified in
         Solr syntax.

> Returns a list of Dashboards matching the search query.


`search_research_questions`(_context_, _data\_dict_)

Does a search for Research Question in the Solr index.

**Parameters:**

* `text` - `str`, _required_, the text to search for.
* `rows` - `int`, _optional_, number of rows to return.
* `start` - `int`, _optional_, offset, start from this result then return `rows`
            results.
* `fq` - `string`/`list`, _optional_, additional filter queries as specified in
         Solr syntax.

> Returns a list of Research Questions matching the search query.

`search_visualizations`(_context_, _data\_dict_)

Does a search for Visualizations in the Solr index.

**Parameters:**

* `text` - `str`, _required_, the text to search for.
* `rows` - `int`, _optional_, number of rows to return.
* `start` - `int`, _optional_, offset, start from this result then return `rows`
            results.
* `fq` - `string`/`list`, _optional_, additional filter queries as specified in
         Solr syntax.

> Returns a list of Visualizations matching the search query.


action.update module
--------------------

`dashboard_update`(_context_, _data\_dict_)

Updates existing dashboard

> :param id :param name :param description :param title :param indicators

`kwh_data_update`(_context_, _data\_dict_)

Store Knowledge Hub data

:param type :param old\_content :param new\_content

`package_update`(_context_, _data\_dict_)

`research_question_update`(_context_, _data\_dict_)

Update research question.



Parameters:

*   **content** (_string_) – The research question.
*   **theme** – Theme of the research question.
*   **sub\_theme** – SubTheme of the research question.
*   **state** (_string_) – State of the research question. Default is active.

`resource_update`(_context_, _data\_dict_)

Override the existing resource\_update to support data upload from data sources



Parameters:

**db\_type** (_string_) – title of the sub-theme

`` `MSSQL` `` :param host: hostname :type host: string :param port: the port :type port: int :param username: DB username :type username: string :param password: DB password :type password: string :param sql: SQL Query :type sql: string

`` `Validation` `` :param schema: schema to be used for validation :type schema: string :param validation\_options: options to be used for validation :type validation\_options: string

`resource_view_update`(_context_, _data\_dict_)

Update a resource view.

To update a resource\_view you must be authorized to update the resource that the resource\_view belongs to.

For further parameters see `resource_view_create()`.



Parameters:

**id** (_string_) – the id of the resource\_view to update

Returns:

the updated resource\_view

Return type:

string

`sub_theme_update`(_context_, _data\_dict_)

Updates an existing sub-theme



Parameters:

*   **name** (_string_) – name of the sub-theme
*   **description** (_string_) – a description of the sub-theme (optional)
*   **theme** (_string_) – the ID of the theme

Returns:

the updated sub-theme

Return type:

dictionary

Updates existing analytical framework Theme

> :param id :param name :param description
