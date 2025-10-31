CREATE TABLE carsusa AS
SELECT *
FROM source.carsusa;
 
-- Step 3: Creating cars table by combining various sources
CREATE TABLE cars AS
SELECT DISTINCT
    TRIM(make) AS make,
    TRIM(model) AS model
FROM carsusa
UNION
SELECT DISTINCT
    TRIM(make) AS make,
    TRIM(model) AS model
FROM carseu
UNION
SELECT DISTINCT
    TRIM(make) AS make,
    TRIM(model) AS model
FROM carasia;
 
-- Step 4: Sorting cars and carsmpg for further processing
CREATE TABLE sorted_cars AS
SELECT *
FROM cars
ORDER BY make, model;
 
CREATE TABLE sorted_carsmpg AS
SELECT *
FROM carsmpg
ORDER BY make, model;
 
-- Step 5: Merge cars and carsmpg based on make and model
CREATE TABLE carsmerge AS
SELECT a.*, b.mpg
FROM sorted_cars a
JOIN sorted_carsmpg b
ON a.make = b.make AND a.model = b.model;
 
-- Step 6: Find the cheapest European SUV with the highest mileage
CREATE TABLE carschoice AS
SELECT *
FROM carsmerge
WHERE origin = 'Europe' AND type = 'SUV'
ORDER BY msrp DESC, mpg_highway DESC;
 
-- Step 7: Print the results
SELECT *
FROM carschoice;
 
