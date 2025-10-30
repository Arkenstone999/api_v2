libname source '/home/u63909936/SASTraining/2. Structuring Data/Data';


data carsusa;
	
	set source.carsusa;
	
run;


proc import datafile='/home/u63909936/SASTraining/2. Structuring Data/Data/carsmpg.xlsx'

out=carsmpg
dbms=xlsx;
getnames=yes;

run;


data cars;
	
	set carsusa carseu carasia;
	
make = strip(make);
model = strip(make);
run;

data carsmpg;

set carsmpg;

make=strip(make);

model=strip(model);

run;     
	
	
proc sort data=cars;

by make model;

proc sort data=carsmpg;

by make model;

run;





/*step 4: merge mileage data */

data carsmerge;

merge cars carsmpg;

by make model;

run;



/*finding the cheapest European SUV with highest mileage */



proc sort data=carsmerge out=carschoice;

by msrp descending mpg_highway;

where origin='Europe' and type ='SUV';

run;



proc print ;

run;


