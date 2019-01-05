import sqlite3

conn = sqlite3.connect('twitter_id.db')

c = conn.cursor()

#c.execute("""CREATE TABLE user_id (
#    id INTEGER PRIMARY KEY,
#    myDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
#    twitterID integer
#    )""")

#c.execute("INSERT INTO user_id (twitterID) VALUES (1)")
#c.execute("SELECT * FROM user_id")
#c.execute("SELECT twitterID FROM user_id ORDER BY id DESC LIMIT 1")
#last_id = c.fetchone()
#print(last_id[0])
conn.commit()

conn.close()
