#wget https://cf-courses-data.s3.us.cloud-object-storage.appdomain.cloud/IBM-BD0225EN-SkillsNetwork/labs/data/cars.csv

#for i in `docker ps | awk '{print $1}' | grep -v CONTAINER`; do docker kill $i; done