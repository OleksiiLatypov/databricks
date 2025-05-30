# import findspark
# findspark.init()
# from pyspark import SparkContext, SparkConf
# from pyspark.sql import SparkSession
# from pyspark.sql.types import StructField, StructType, IntegerType, StringType


# spark = SparkSession.builder \
#         .master('spark://theiadocker-latypovoleks:7077') \
#         .config('spark.executors.cores', '1') \
#         .config('spark.executor.memory', '512m') \
#         .getOrCreate()
    
# df = spark.createDataFrame([(1, 'foo'), (2, 'bar')],
#                             StructType(
#                                 [
#                                 StructField('id', IntegerType(), False),
#                                 StructField('txt', StringType(), False)
#                                 ]
#                             )
#                         )

# print(df.dtypes)

# print('\nDataFrame:')
# df.show()



#wget https://archive.apache.org/dist/spark/spark-3.3.3/spark-3.3.3-bin-hadoop3.tgz && tar xf spark-3.3.3-bin-hadoop3.tgz && rm -rf spark-3.3.3-bin-hadoop3.tgz


import findspark
findspark.init()
from pyspark import SparkContext, SparkConf
from pyspark.sql import SparkSession
from pyspark.sql.types import StructField, StructType, IntegerType, StringType

spark = SparkSession.builder \
    .master('spark://theiadocker-yourname:7077') \
    .config('spark.executor.cores', '1') \
    .config('spark.executor.memory', '512m') \
    .getOrCreate()

df = spark.createDataFrame(
    [
        (1, "foo"),
        (2, "bar"),
    ],
    StructType(
        [
            StructField("id", IntegerType(), False),
            StructField("txt", StringType(), False),
        ]
    ),
)
print(df.dtypes)

print("\nDataFrame:")
df.show()