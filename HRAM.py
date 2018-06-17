##This code is called HRAM - Habitual Route Analysis Method

#import libraries
import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import sys

if sys.version_info[0] < 3:
#Folder input 
#this folder will contain the year worth of data 
#each folder will have line shapefiles within it representative of one day
    year_folder = str(raw_input('Path to data:  '))

#the  Spatial Reference System Identifier (SRID) of the 
#shapefiles. These shapefiles MUST be projected 
    SRID = str(raw_input('SRID USED?: '))

#This is the line of sight for each animal , the unit of measurement 
#is based on the SRID inputted above

    buffer_amt = str(raw_input('How much would you like to buffer for ? (keep in mind the unit measurement is dependent on your SRID) :'))
    password = str(raw_input('password for database: '))
    postgres = str(raw_input('Postgres bin path:  '))
else:
    #this changes the input type to be supported by python 3
    year_folder = str(input('Path to data:  '))
    SRID = str(input('SRID USED?: '))
    buffer_amt = str(input('How much would you like to buffer for ? (keep in mind the unit measurement is dependent on your SRID) :'))
    password = str(input('Password for database:  '))
    postgres = str(input('Postgres bin path:  '))
    

def get_data(directory, folderlist):

    #iterate through the folder where each month is located
    for subdir, dirs, files in os.walk(directory):
        for f in files:
            #grab all the files that are shapefiles
            if f.endswith('.shp'):
              #this will place each day within its corresponding month list
              folderlist.append(f)
     #returns the  list created         
    return folderlist

def upload (folderlist2, directory, SRID, dir_path):
    #run the shape to pgsql command..which will import shapefile to a database
    for shapefile in folderlist2:
        
        #creates a full path to each day's shapefile within a month's list
        path = directory + '\\' + shapefile  
        #this command is ran through the postgresql bin
        #this will upload each day as its own table in the database
        cmd = 'shp2pgsql -I -s {2} "{0}" public."{1}" | psql -U postgres -p 5432 -d test1'.format(path,shapefile, SRID)
        print (cmd)
        #this path must be inputted by user where bin is located
        ##
        ##
        ##
        ##This path
        #dir_path= ('C:\\Program Files\\PostgreSQL\\9.5\\bin')
        password = 'postgres'
        password_cmd = 'set PGPASSWORD = {0}'.format(password)
        os.chdir(dir_path)
        #execute above command in the postgreSQL bin 
        os.system(password_cmd)
        os.system(cmd)
       
#select table names that match within list of each month and insert into month table
def table_insert (month, data, monthlist):
    #establish a connection to the databbase
    connection = psycopg2.connect( "host= 'localhost' user= 'postgres' password='postgres' dbname = 'test1'" )
    connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    curs = connection.cursor()
  #iterate through each month from 01 - 12
    for monthname in monthlist:
        #when the month name inputed matches the month name in the list
        if monthname == month:
            #This will iterate through each day shapefile within the month             
            for shp in data:
                #Creating two different variable one that is lower case ,
                #and one to be inserted into table for ID
                name = shp[:6]
                name_string = "'" + name + "'"
                lower_shp = shp.lower()
                #this will try to add a column to each table and insert 
                #a naming convention  (april01 or 0401)
                #then it will insert the day into the month table
                try:
                    curs.execute('ALTER TABLE public."{0}" ADD daynum VARCHAR(10)'.format(lower_shp))
                    curs.execute('UPDATE public."{0}" SET daynum = {1};'.format(lower_shp, name_string))
                    curs.execute('INSERT INTO {0} SELECT daynum, geom FROM public."{1}" ;'.format(monthname,lower_shp))
                                        
                except:
                    print (lower_shp)
                    
 #Buffer individual segements from one month and compare them with other monthss
def buffer_segments(data,month,buffer_amt, monthlist):  
    #establish a connection to the database
    connection = psycopg2.connect( "host= 'localhost' user= 'postgres' password='postgres' dbname = 'test1'" )
    connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    curs1 = connection.cursor()    
   
    #iterate through each month
    for month_name in monthlist:
    #if the month is the same as the input month
        if month_name == month:
            #this is the table where each segment will be placed for the corresponding
            #month
            month_segment = month  + '_segments'
            #each day within a month
            for day in data:
                #will be compared to every other month
                for each_month in monthlist:
                    #as long as it is not the month for which the day is already in
                    if each_month != month:
                        try:                           
                            lower_day = day.lower()
                            #this SQL statement will select all geometries that
                            # is within the animals sight range and place it in the
                            #corresponding  month_segment
                            curs1.execute('INSERT INTO public."{0}" SELECT buffer.daynum, {1}.daynum, ST_Intersection({1}.geom, buffer.geom) FROM {1}, (SELECT daynum, ST_Buffer(public."{2}".geom, {3}) as geom FROM public."{2}") as buffer WHERE ST_Intersects({1}.geom, buffer.geom)'.format(month_segment,each_month,lower_day,buffer_amt))
                        #eventually will write to a document stating what .shp 's failed
                        except:
                            print (lower_day)
                            value_placeholder = 0
    curs1.close()
#counts how many distinct days repeat each day within another month                            
def get_count(monthlist):
    connection = psycopg2.connect( "host= 'localhost' user= 'postgres' password='postgres' dbname = 'test1'" )
    connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    curs2 = connection.cursor() 
    for month in monthlist:
        month_segment = month  + '_segments'
        curs2.execute('ALTER TABLE {0} ADD num_repeat_path integer'.format(month))
        try:
            #SQL statement that counts the distinct paths, joins table
            #then updates another table to include the number of times
            #the path segment repeats.
            curs2.execute('UPDATE public.{0} SET num_repeat_path = seg_count.count FROM (SELECT daynum, count(distinct(repeated)) FROM {1} GROUP BY daynum) as seg_count WHERE seg_count.daynum = {0}.daynum'.format(month,month_segment))
        except:
            print ('Did not execute')
                
                
def output_dump(year_folder, monthlist, dir_path):
    output_folder = year_folder + '\\output'
    os.makedirs(output_folder)
    #dir_path= ('C:\\Program Files\\PostgreSQL\\9.5\\bin')
    
    for month in monthlist: 
        segment = month + '_segments'
        seg_path = output_folder + '\\' + segment 
        month_path = output_folder + '\\' + month
        cmd = 'pgsql2shp -f "{0}" -h localhost -u postgres -P postgres test1 public.{1} -g public.{1}.geom'.format(seg_path, segment)
        cmd2 = 'pgsql2shp -f "{0}" -h localhost -u postgres -P postgres test1 public.{1} -g public.{1}.geom'.format(month_path, month)
        os.chdir(dir_path)
        #execute above command in the postgreSQL bin location
        os.system(cmd)
        os.system(cmd2)
    
def main (year_folder, SRID, buffer_amt, postgres):
    
    #The extension to each month
    jan_dir = str(year_folder) + '\\01'
    feb_dir = str(year_folder) + '\\02'
    march_dir =str(year_folder) + '\\03'
    april_dir = str(year_folder) + '\\04'
    may_dir = str(year_folder) + '\\05'
    june_dir = str(year_folder) + '\\06'
    july_dir = str(year_folder) + '\\07'
    aug_dir = str(year_folder) + '\\08'
    sept_dir = str(year_folder) + '\\09'
    octob_dir = str(year_folder) + '\\10'
    nov_dir = str(year_folder) + '\\11'
    dec_dir = str(year_folder) + '\\12'
    
    #32736
    #Connect to PGadmin, in order to create database 
    con = psycopg2.connect("host= 'localhost' user= 'postgres' password= 'postgres'")
    dbname = 'test1'
    con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = con.cursor()
    cur.execute('DROP DATABASE IF EXISTS ' + dbname)
    cur.execute('CREATE DATABASE ' + dbname)
    con.close()

    #connect to the database just created
    conn = psycopg2.connect( "host= 'localhost' user= 'postgres' password='postgres' dbname = 'test1'" )
    cur = conn.cursor()
    conn.autocommit = True
    cur.execute('CREATE EXTENSION IF NOT EXISTS postgis;')

    #Create empty table to populate month data
    monthlist = ('jan', 'feb', 'march', 'april', 'may', 'june', 'july', 'aug', 'sept', 'octob', 'nov', 'dec')
    cur.execute('CREATE SEQUENCE seg_seq;')
    for x in monthlist:
        #create empty tables of entire month
        cur.execute('CREATE TABLE public.'+ x + '_segments (daynum varchar(10), repeated varchar(10), geom geometry(geometry, {0}));'.format(SRID))
        cur.execute('CREATE TABLE public.'+ x + ' ( daynum varchar(10) NOT NULL, geom geometry(MultiLineString, {0}), PRIMARY KEY (daynum));'.format(SRID))
    
    #create empty lists for each month
    jan = [] 
    feb = []
    march = []
    april = []
    may = []
    june = []
    july = []
    aug = []
    sept = []
    octob = []
    nov =[]
    dec = []

    #Send each month to receive the data from the users inputted folders
    
    #Get month 1 - January
    jan_data = get_data(jan_dir, jan)
    upload(jan_data, jan_dir,SRID, postgres)
    j = 'jan'
    table_insert(j, jan_data, monthlist)

    #Get month 2 - February
    feb_data = get_data(feb_dir, feb)
    upload(feb_data, feb_dir, SRID, postgres)
    f = 'feb'
    table_insert(f, feb_data,monthlist)

    #Get month 3 - March
    march_data = get_data(march_dir, march)
    upload(march_data, march_dir, SRID, postgres)
    mr = 'march'
    table_insert(mr, march_data, monthlist)
    
    #Get month 4 - April
    april_data = get_data(april_dir, april)
    upload(april_data, april_dir, SRID, postgres)
    a = 'april'
    table_insert(a, april_data,monthlist)
 
    #Get month 5 - May
    may_data = get_data(may_dir, may)
    upload(may_data, may_dir, SRID, postgres)
    m = 'may'
    table_insert(m, may_data, monthlist)
    
    #Get month 6 - June
    june_data = get_data(june_dir, june)
    upload(june_data, june_dir, SRID, postgres)
    ju = 'june'
    table_insert(ju, june_data, monthlist)
    
    #Get month 7 - July
    july_data = get_data(july_dir, july)
    upload(july_data, july_dir, SRID, postgres)
    jy = 'july'
    table_insert(jy, july_data, monthlist)
    
    #Get month 8 - August
    aug_data = get_data(aug_dir, aug)
    upload(aug_data, aug_dir, SRID, postgres)
    au = 'aug'
    table_insert(au, aug_data, monthlist)
    
    #Get month 9 - September
    sept_data = get_data(sept_dir, sept)
    upload(sept_data, sept_dir, SRID, postgres)
    s = 'sept'
    table_insert(s, sept_data, monthlist)   
    
    #Get month 10 - October 
    octob_data = get_data(octob_dir, octob)
    upload(octob_data, octob_dir, SRID, postgres)
    o = 'octob'
    table_insert(o, octob_data, monthlist)
    
    #Get month 11 - November
    nov_data = get_data(nov_dir, nov)
    upload(nov_data, nov_dir, SRID, postgres)
    n = 'nov'
    table_insert(n, nov_data, monthlist)
    
    #Get month 12- December 
    dec_data = get_data(dec_dir, dec)
    upload(dec_data, dec_dir, SRID, postgres)
    d = 'dec'
    table_insert(d, dec_data, monthlist)
    
    buffer_segments(jan_data, j, buffer_amt, monthlist)
    buffer_segments(feb_data, f,buffer_amt, monthlist)
    buffer_segments(march_data, mr, buffer_amt, monthlist)
    buffer_segments(april_data, a, buffer_amt, monthlist)
    buffer_segments(may_data, m, buffer_amt, monthlist)
    buffer_segments(june_data, ju, buffer_amt, monthlist)
    buffer_segments(july_data, jy, buffer_amt, monthlist)
    buffer_segments(aug_data, au, buffer_amt,monthlist)
    buffer_segments(sept_data, s, buffer_amt, monthlist)
    buffer_segments(octob_data, o, buffer_amt, monthlist)
    buffer_segments(nov_data, n, buffer_amt, monthlist)
    buffer_segments(dec_data, d, buffer_amt, monthlist)

    get_count(monthlist)    
    output_dump(year_folder, monthlist, postgres)

    cur.close()
    conn.close()

    ## [REQUIRES INPUT FROM PLUGIN]



    ## Compare (CLIP?) merged segment for month A againsts BCDEF..etc

    print ('end')
main(year_folder, SRID, buffer_amt, postgres)
