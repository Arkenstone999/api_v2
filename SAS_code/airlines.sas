/* Définir la bibliothèque de sortie */
libname outlib '/home/u63909936/SAS2PY';

/* Fichier source */
filename reffile '/home/u63909936/SASTraining/1. Preparing Data/Data/airlines.txt';

/* Table principale airlines */
data airlines;
    infile reffile;
    format Revenue Totalassets Investmentsfunds adjustedassets dollar9.2;
    input Airline $ 1-20 Length 22-28 Speed 30-36 Dailyflighttime 38-44 
          Populationserved 46-52 TotalopCost 54-60 Revenue 62-68 Loadcap 70-76 
          Availablecap 78-84 Totalassets 86-92 Investmentsfunds 94-100 Adjustedassets 102-108;

    if Totalopcost < 50 then RATING = 5;
    else if 50 < Totalopcost < 100 then RATING = 4;
    else if 100 < Totalopcost < 150 then RATING = 3;
    else if 150 < Totalopcost < 200 then RATING = 2;
    else if 200 < Totalopcost then RATING = 1; 
run;

/* Sauvegarde airlines en natif SAS */
data outlib.airlines;
    set airlines;
run;

/* Table airlinesP (filtrée) */
data airlinesP;
    set airlines;
    if substr(Airline, 1, 1) = 'P';
run;

/* Sauvegarde airlinesP */
data outlib.airlinesP;
    set airlinesP;
run;

/* Agrégation HBAR : moyenne TotalopCost par RATING */
proc means data=airlines noprint;
    class RATING;
    var TotalopCost;
    output out=chart_hbar mean=Mean_TotalopCost;
run;

/* Sauvegarde chart_hbar */
data outlib.chart_hbar;
    set chart_hbar;
run;

/* Agrégation VBAR : distribution des fréquences par RATING */
proc freq data=airlines noprint;
    tables RATING / out=chart_vbar;
run;

/* Sauvegarde chart_vbar */
data outlib.chart_vbar;
    set chart_vbar;
run;

/* Proc SQL (just sql) FASTPLANE : sélectionner l’avion le plus rapide */
/* be careful with duplicates */
proc sql noprint;
    create table fastplane as
    select Airline, Speed
    from airlines
    having Speed = max(Speed);
quit;

/* Sauvegarde fastplane */
data outlib.fastplane;
    set fastplane;
run;