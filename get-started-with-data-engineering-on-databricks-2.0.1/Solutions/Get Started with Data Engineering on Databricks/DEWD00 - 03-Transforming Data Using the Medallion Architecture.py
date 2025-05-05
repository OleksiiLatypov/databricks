# Databricks notebook source
# MAGIC %md
# MAGIC
# MAGIC <div style="text-align: center; line-height: 0; padding-top: 9px;">
# MAGIC   <img src="https://databricks.com/wp-content/uploads/2018/03/db-academy-rgb-1200px.png" alt="Databricks Learning">
# MAGIC </div>
# MAGIC

# COMMAND ----------

# MAGIC %md
# MAGIC # Transforming Data Using the Medallion Architecture
# MAGIC <br></br>
# MAGIC ![medallion_architecture](./Includes/images/medallion_architecture.png)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Classroom Setup
# MAGIC
# MAGIC Run the following cell to configure your working environment for this course.
# MAGIC
# MAGIC **NOTE:** The `DA` object is only used in Databricks Academy courses and is not available outside of these courses. It will dynamically reference the information needed to run the course.

# COMMAND ----------

# MAGIC %run ./Includes/Classroom-Setup-03

# COMMAND ----------

# MAGIC %md
# MAGIC ## A. Configure and Explore Your Environment

# COMMAND ----------

# MAGIC %md
# MAGIC 1. Set the default catalog to **dbacademy** and the schema to your specific schema. Then, view the available tables to confirm that no tables currently exist in your schema.

# COMMAND ----------


# Set the catalog and schema
spark.sql(f"USE CATALOG {DA.catalog_name}")
spark.sql(f"USE SCHEMA {DA.schema_name}")

# Display available tables in your schema
spark.sql('SHOW TABLES').display()

# COMMAND ----------

# MAGIC %md
# MAGIC 2. View the available files in your schema's **myfiles** volume. Confirm that the volume contains two CSV files, **employees.csv** and **employees2.csv**.

# COMMAND ----------

spark.sql(f"LIST '/Volumes/{DA.catalog_name}/{DA.schema_name}/myfiles/' ").display()

# COMMAND ----------

# MAGIC %md
# MAGIC ## B. Simple Example of the Medallion Architecture
# MAGIC
# MAGIC **Objective**: Create a pipeline that can be scheduled to run automatically. The pipeline will:
# MAGIC
# MAGIC 1. Ingest all CSV files from the **myfiles** volume and create a bronze table.
# MAGIC 2. Prepare the bronze table by adding new columns and create a silver table.
# MAGIC 3. Create a gold aggregated table for consumers.

# COMMAND ----------

# MAGIC %md
# MAGIC ### BRONZE
# MAGIC **Objective:** Create a table using all of the CSV files in the **myfiles** volume.

# COMMAND ----------

# MAGIC %md
# MAGIC 1. Execute the cell to perform the following:
# MAGIC     - The DROP TABLE IF EXISTS statement drops the **current_employees_bronze** table if it already exists for demonstration purposes.
# MAGIC     - The CREATE TABLE IF NOT EXISTS statement creates the Delta table **current_employees_bronze** if it doesn't already exist and defines the table columns.
# MAGIC     - The COPY INTO statement:
# MAGIC         - loads all the CSV files from the **myfiles** volume in your schema into the **current_employees_bronze** table and creates a new column named **InputFile** that displays the file from where the data came. 
# MAGIC         - It uses the first row as headers and infers the schema from the CSV files.
# MAGIC     - The query will display all rows from the **current_employees_bronze** table.
# MAGIC
# MAGIC     Confirm that the table has 6 rows and 5 columns.
# MAGIC
# MAGIC     **NOTE:** The  [input_file_name](https://docs.databricks.com/en/sql/language-manual/functions/input_file_name.html) function is not available on Unity Catalog. You can get metadata information for input files with the [_metadata](https://docs.databricks.com/en/ingestion/file-metadata-column.html) column.

# COMMAND ----------

# Drop the table if it exists for demonstration purposes
spark.sql('DROP TABLE IF EXISTS current_employees_bronze')

# Create an empty table and columns
spark.sql('''
  CREATE TABLE IF NOT EXISTS current_employees_bronze (
  ID INT,
  FirstName STRING,
  Country STRING,
  Role STRING,
  InputFile STRING
  )
''')

# Create the bronze raw ingestion table and include the CSV file name for the rows
spark.sql(f'''
  COPY INTO current_employees_bronze
  FROM (
      SELECT *, 
             _metadata.file_name AS InputFile               -- Add the input file name to the bronze table
      FROM '/Volumes/{DA.catalog_name}/{DA.schema_name}/myfiles/'
  )
  FILEFORMAT = CSV
  FORMAT_OPTIONS ('header' = 'true', 'inferSchema' = 'true')
''')


# View the bronze table
spark.sql('SELECT * FROM current_employees_bronze').display()

# COMMAND ----------

# MAGIC %md
# MAGIC ### SILVER
# MAGIC **Objective**: Transform the bronze table and insert the resulting rows into the silver table.
# MAGIC
# MAGIC 1. Create and display a temporary view named **temp_view_employees_silver** from the **current_employees_bronze** table. 
# MAGIC
# MAGIC     The view will:
# MAGIC     - Select the columns **ID**, **FirstName**, **Country**.
# MAGIC     - Convert the **Role** column to uppercase.
# MAGIC     - Add two new columns: **TimeStamp** and **Date**.
# MAGIC
# MAGIC     Confirm that the results display 6 rows and 6 columns.

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Create a temporary view to use to merge the data into the final silver table
# MAGIC CREATE OR REPLACE TEMP VIEW temp_view_employees_silver AS 
# MAGIC SELECT 
# MAGIC   ID,
# MAGIC   FirstName,
# MAGIC   Country,
# MAGIC   upper(Role) as Role,                 -- Upcase the Role column
# MAGIC   current_timestamp() as TimeStamp,    -- Get the current datetime
# MAGIC   date(timestamp) as Date              -- Get the date
# MAGIC FROM current_employees_bronze;
# MAGIC
# MAGIC
# MAGIC -- Display the results of the view
# MAGIC SELECT * 
# MAGIC FROM temp_view_employees_silver;

# COMMAND ----------

# MAGIC %md
# MAGIC 2. Create a new table named **current_employees_silver** and insert rows from the **temp_view_employees_silver** view that are not already present in the table based on the **ID** column.
# MAGIC
# MAGIC     Confirm the following:
# MAGIC     - **num_affected rows** is *6*
# MAGIC     - **num_updated_rows** is *0*
# MAGIC     - **num_deleted rows** is *0*
# MAGIC     - **num_inserted_rows** is *6*

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Dropping the table for demonstration purposes
# MAGIC DROP TABLE IF EXISTS current_employees_silver;
# MAGIC
# MAGIC
# MAGIC -- Create an empty table and specify the column data types
# MAGIC CREATE TABLE IF NOT EXISTS current_employees_silver (
# MAGIC   ID INT,
# MAGIC   FirstName STRING,
# MAGIC   Country STRING,
# MAGIC   Role STRING,
# MAGIC   TimeStamp TIMESTAMP,
# MAGIC   Date DATE
# MAGIC );
# MAGIC
# MAGIC
# MAGIC -- Insert records from the view when not matched with the target silver table
# MAGIC MERGE INTO current_employees_silver AS target 
# MAGIC   USING temp_view_employees_silver AS source
# MAGIC   ON target.ID = source.ID
# MAGIC   WHEN NOT MATCHED THEN INSERT *            -- Insert rows if no match

# COMMAND ----------

# MAGIC %md
# MAGIC 3. View the **current_employees_silver** table. Confirm the table contains all 6 employees.

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT * 
# MAGIC FROM current_employees_silver;

# COMMAND ----------

# MAGIC %md
# MAGIC 4. Run the same MERGE INTO statement again. Note that since all the **ID** values matched, no rows were inserted into the **current_employees_silver**  table.

# COMMAND ----------

# MAGIC %sql
# MAGIC MERGE INTO current_employees_silver AS target 
# MAGIC   USING temp_view_employees_silver AS source
# MAGIC   ON target.ID = source.ID
# MAGIC   WHEN NOT MATCHED THEN INSERT *

# COMMAND ----------

# MAGIC %md
# MAGIC ### GOLD
# MAGIC **Objective:** Aggregate the silver table to create the final gold table.

# COMMAND ----------

# MAGIC %md
# MAGIC 1. Create a temporary view named **temp_view_total_roles** that aggregates the total number of employees by role. Then, display the results of the view.

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TEMP VIEW temp_view_total_roles AS 
# MAGIC SELECT
# MAGIC   Role, 
# MAGIC   count(*) as TotalEmployees
# MAGIC FROM current_employees_silver
# MAGIC GROUP BY Role;
# MAGIC
# MAGIC
# MAGIC SELECT *
# MAGIC FROM temp_view_total_roles;

# COMMAND ----------

# MAGIC %md
# MAGIC 2. Create the final gold table named **total_roles_gold** with the specified columns.

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Dropping the table for demonstration purposes
# MAGIC DROP TABLE IF EXISTS total_roles_gold;
# MAGIC
# MAGIC CREATE TABLE IF NOT EXISTS total_roles_gold (
# MAGIC   Role STRING,
# MAGIC   TotalEmployees INT
# MAGIC );

# COMMAND ----------

# MAGIC %md
# MAGIC 3. Insert all rows from the aggregated temporary view **temp_view_total_rows** into the **total_roles_gold** table, overwriting the existing data in the table. This will allow you to see the history as the gold table is updated.
# MAGIC
# MAGIC     Confirm the following:
# MAGIC     - **num_affected_rows** is *4*
# MAGIC     - **num_inserted_rows** is *4*

# COMMAND ----------

# MAGIC %sql
# MAGIC INSERT OVERWRITE TABLE total_roles_gold
# MAGIC SELECT * 
# MAGIC FROM temp_view_total_roles;

# COMMAND ----------

# MAGIC %md
# MAGIC 4. Query the **total_roles_gold** table to view the total number of employees by role.

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT *
# MAGIC FROM total_roles_gold;

# COMMAND ----------

# MAGIC %md
# MAGIC ## C. Data Governance and Security
# MAGIC **Objectives:** View the lineage of the **total_roles_gold** table and learn how to set its permissions.

# COMMAND ----------

# MAGIC %md
# MAGIC ### 1. Complete the following to open your schema in the **Catalog Explorer**.
# MAGIC - a. Select the Catalog icon in the left navigation bar. 
# MAGIC - b. Type the module's catalog name in the search bar (*dbacademy*).
# MAGIC - c. Select the refresh icon to refresh the **dbacademy** catalog.
# MAGIC - d. Expand the **dbacademy** catalog. Within the catalog, you should see a variety of schemas (databases).
# MAGIC - e. Find and select your schema. You can locate your schema in the setup notes in the first cell or in the top widget bar under the **my_schema** parameter. 
# MAGIC - f.  Click the options icon to the right of your schema and choose **Open in Catalog Explorer**.
# MAGIC - g. Notice that the three tables we created in the demo: **current_employees_bronze**, **current_employees_silver** and **total_roles_gold** are shown in the **Catalog Explorer** for your schema.
# MAGIC - h. In the **Catalog Explorer** select the **total_roles_gold** table.
# MAGIC
# MAGIC Leave the **Catalog Explorer** tab open.

# COMMAND ----------

# MAGIC %md
# MAGIC ### 2. Complete the following to view the **total_roles_gold** table's permissions, history, lineage and insights in Catalog Explorer: 
# MAGIC - a. **Permissions**. 
# MAGIC   - Select the **Permissions** tab. This will display all permissions on the table. Currently the table does not have any permissions set.
# MAGIC   - Select **Grant**. This allows you to add multiple principals and assign privileges to them. Users must have access to the Catalog and Schema of the table.
# MAGIC   - Select **Cancel**. 
# MAGIC - b. **History**
# MAGIC   - Select the **History** tab. This will display the table's history. The **total_roles_gold** table currently has two versions.
# MAGIC - c. **Lineage**
# MAGIC   - Select the **Lineage** tab. This displays the table's lineage. Confirm that the **current_employees_silver** table is shown.
# MAGIC   - Select the **See lineage graph** button. This displays the table's lineage visually. You can select the **+** icon to view additional information.
# MAGIC   - Close out of the lineage graph.
# MAGIC - d. **Insights**
# MAGIC   - Select the **Insights** tab. You can use the Insights tab in **Catalog Explorer** to view the most frequent recent queries and users of any table registered in Unity Catalog. The Insights tab reports on frequent queries and user access for the past 30 days.
# MAGIC - e. Close the **Catalog Explorer** browser tab.

# COMMAND ----------

# MAGIC %md
# MAGIC ##D. Cleanup
# MAGIC 1. Drop views and tables.

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Drop the temporary views
# MAGIC DROP VIEW IF EXISTS temp_view_total_roles;
# MAGIC DROP VIEW IF EXISTS temp_view_employees_silver;
# MAGIC
# MAGIC -- Drop the tables
# MAGIC DROP TABLE IF EXISTS current_employees_bronze;
# MAGIC DROP TABLE IF EXISTS current_employees_silver;
# MAGIC DROP TABLE IF EXISTS total_roles_gold;

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC &copy; 2025 Databricks, Inc. All rights reserved.<br/>
# MAGIC Apache, Apache Spark, Spark and the Spark logo are trademarks of the 
# MAGIC <a href="https://www.apache.org/">Apache Software Foundation</a>.<br/>
# MAGIC <br/><a href="https://databricks.com/privacy-policy">Privacy Policy</a> | 
# MAGIC <a href="https://databricks.com/terms-of-use">Terms of Use</a> | 
# MAGIC <a href="https://help.databricks.com/">Support</a>