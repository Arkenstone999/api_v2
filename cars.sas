%_eg_conditional_dropds(WORK.AWB_REVREC_EU);

PROC SQL;
   CREATE TABLE WORK.AWB_REVREC_EU AS 
   SELECT DISTINCT t1.SYSTEM_SOURCE_CD, 
          t1.SHP_DT, 
          t1.SHP_NBR, 
          t1.SHP_TRK_NBR, 
          t1.ORIG_CTRY_CD, 
          t1.DEST_CTRY_CD, 
          t1.AUTO_FLAG, 
          t1.SVC_BAS_CD, 
          t3.PRODUCT_DESC, 
          t2.PKG_TYP_DESC, 
          t1.SHP_CUST_NBR, 
          t1.PAYER_TYPE, 
          t1.PAYR_CUST_NBR, 
          t1.BILL_WGT AS BILL_WGT_LB, 
          t1.PACKS, 
          t1.NET_REV_AMT_EX_DFS_STD
      FROM CCI_SVC1.AWB_REVREC t1, SAS_LKUP.PKG_TYP_CD t2, SAS_LKUP.PRODUCT_LKUP t3
      WHERE (t1.PKG_TYP_CD = t2.PKG_TYP_CD AND t1.PRODUCT_CD = t3.PRODUCT_CD) AND (t1.SHP_YYYYMM = '202206' AND 
           t1.IC_IE_DOM_INT = 'DOM' AND t1.ORIG_CTRY_CD IN 
           (
           'AT',
           'BE',
           'CH',
           'DE',
           'DK',
           'ES',
           'FI',
           'FR',
           'GB',
           'HU',
           'IE',
           'IT',
           'LU',
           'NL',
           'NO',
           'SE',
           'CZ',
           'PL',
           'SK'
           ) AND t1.SVC_BAS_CD IN 
           (
           '01',
           '22',
           '23',
           '24',
           '25',
           '26',
           '32'
           ) AND t1.SERVICE_FAIL_CD NOT IN 
           (
           ''
           ))
      ORDER BY t1.SYSTEM_SOURCE_CD,
               t1.ORIG_CTRY_CD,
               t1.DEST_CTRY_CD,
               t1.SVC_BAS_CD,
               t2.PKG_TYP_DESC,
               t1.AUTO_FLAG,
               t1.SHP_CUST_NBR,
               t1.PAYER_TYPE,
               t1.PAYR_CUST_NBR;
QUIT;