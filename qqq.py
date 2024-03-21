import pymongo

client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["MyJavDB"]
movie_collection = db["movie"]
actor_collection = db["actor"]
movie_index = movie_collection.index_information()
actor_index = actor_collection.index_information()
print(movie_index)
print(actor_index)
{"_id_": {"v": 2, "key": [("_id", 1)]}, "url_1": {"v": 2, "key": [("url", 1)], "background": False, "unique": True, "sparse": False}}
