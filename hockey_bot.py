#Jaspal Bainiwal
#This is my twitter bot which tweets NHL game status that are to be played for the current day.
import datetime
import requests
import pytz
import tweepy
import time
from keys import *
import sqlite3

auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
auth.set_access_token(ACCESS_KEY, ACCESS_SECRET)
api = tweepy.API(auth)

"""This function creates a dictionary for each team in the nhl with keys being
the nhl team name and the value as the nhl teams abbreviation. Then the function returns
the created dictionary"""
def create_team_list():
    url = "https://statsapi.web.nhl.com/api/v1/teams"
    team_list = dict()
    all_teams = requests.get(
       url,
       headers={"Accept": "application/json"}
    ).json()
    all_teams = all_teams["teams"]
    for x in all_teams:
        team_list.update({x["name"]: x["abbreviation"]}) 
    return team_list
 
"""This function creates key value pairs with the key being awayVshome and the 
value being the gameID that the NHL has assigned for that particular game"""
def daily_game_list(all_teams):
    my_date = datetime.datetime.now(pytz.timezone('US/Pacific')).strftime('%Y-%m-%d')
    games_today = dict()
    url = "https://statsapi.web.nhl.com/api/v1/schedule"
    response_json = requests.get(
       url,
       headers={"Accept": "application/json"},
       params={"date": my_date}
    ).json()
    
    games = response_json["dates"][0]["games"]
    for x in games:
        #get abbreviation for the teams for that particular game 
        away_abrv = all_teams.get(x["teams"]["away"]["team"]["name"])
        home_abrv = all_teams.get(x["teams"]["home"]["team"]["name"])
        
        id_link = x["link"]
        id = id_link[13:23]
        games_today.update({away_abrv+'vs'+home_abrv: id})
    return games_today

#changes game time from utc ISO 8601 to pst 
def convert_time(date):
        date = date[:16]
        utc_date = datetime.datetime.strptime(date, '%Y-%m-%dT%H:%M').replace(tzinfo=pytz.utc)
        pst_date = utc_date.astimezone(pytz.timezone('US/Pacific')).strftime('%-I:%M %p on %A %b %d')
        return pst_date

"""creates a tweet if the game has not started it tweets back the time the game starts
If the game has started it tweets one of three options based on game status. If the game is in play, period
ended, or game finished. If the game is in play or the quarter has ended I call the nhl api for the line score 
and extract the goals, time, period information. If the game has not started I call the feed/live request to get
gametime information. """
def game_tweet(game_id, games_today):
    url = "https://statsapi.web.nhl.com/api/v1/game/"+game_id+"/linescore"
    game_response = requests.get(
        url,
        headers={"Accept": "application/json"}
        ).json()
    currentPeriod = game_response["currentPeriod"]
    if currentPeriod == 0:
        game_time_response = requests.get(
            "https://statsapi.web.nhl.com/api/v1/game/"+game_id+"/feed/live",
            headers={"Accept": "application/json"}
            ).json()
        date = game_time_response["gameData"]["datetime"]["dateTime"]
        date = convert_time(date)
        away_abrv = game_time_response["gameData"]["teams"]["away"]["abbreviation"]
        home_abrv = game_time_response["gameData"]["teams"]["home"]["abbreviation"]
        tweet_message = " The game has not started. The puck will drop at " + date + " #" + away_abrv + "vs" + home_abrv
    else:
        home_goals = str(game_response["teams"]["home"]["goals"])
        away_goals = str(game_response["teams"]["away"]["goals"])
        home_name = game_response["teams"]["home"]["team"]["name"]
        away_name = game_response["teams"]["away"]["team"]["name"]
        period = game_response["currentPeriodOrdinal"]
        game_time = game_response["currentPeriodTimeRemaining"]
        #using list comprehension to find key by searching the value in a dictionary
        hashtag = [abrv for abrv, id in games_today.items() if id == game_id]
        if game_time == 'END':
            tweet_message = " The game has ended the " + period + " period. The score is " + away_name + " " + away_goals + " to " + home_name + " " + home_goals + ". #" + hashtag[0]
        elif game_time == 'Final':
            tweet_message = " The game has finished. The final score " + away_name + " " + away_goals + " to " + home_name + " " + home_goals + ". #" + hashtag[0]
        else:
            tweet_message = " The game is currently in the " + period + " period with " + game_time + " remaining. The current score is " + away_name + " " + away_goals + " to " + home_name + " " + home_goals + ". #" + hashtag[0]
        return tweet_message
#creates a string of twitter hashtags for all the games to be played for that day.
#The hashtags are in the format AWAY vs HOME 
def schedule_tweet(games_today):
    x = games_today.keys()
    str = ""
    for index in x:
        str += "#" + index + " "
    return str


def tweet(games_today):
    #created lower case dictionary keys so it will be easier to cover all edge cases with hashtags
    games_today_lower = {key.lower(): x for key, x in games_today.items()}
    #find the last twitter mention id stored in the database
    c = conn.cursor()
    c.execute("SELECT twitterID FROM user_id ORDER BY id DESC LIMIT 1")
    last_id = c.fetchone()
    tweets = api.mentions_timeline(last_id[0], tweet_mode="extended")
    for x in reversed(tweets):
        #find all hashtags tweeted to the twitter account
        hashtags = x.entities["hashtags"]
        #count how many hashtags were used in the twitter message
        hashtag_len = len(hashtags)
        counter = 1
        tweeted_back = False
        for y in hashtags:
            game_id = games_today_lower.get(y["text"].lower())
            #check if the gameID is found in the dictionary if so then also check
            #if the account hasn't tweeted back yet.
            if (game_id != None) and (tweeted_back == False):
                tweet_msg = game_tweet(game_id, games_today)
                api.update_status("@" + x.user.screen_name + tweet_msg, x.id)
                print("tweeted back and hashtag matched one of the games today")
                #once tweeted back store the mention id into the sqlite database.
                c.execute("INSERT INTO user_id (twitterID) VALUES (" + str(x.id) + ")")
                conn.commit()
                print("mention id " + str(x.id))
                tweeted_back = True
            #if after checking all the hashtags and the gameID was not found because
            #the hashtags sent were not in right format then on the last hashtag send general tweet
            #however also tweeted back has to be false so if the hashtag with correct format was tweeted at
            #then an extra tweet won't be sent.
            elif hashtag_len == counter and tweeted_back == False:
                schedule = schedule_tweet(games_today)
                tweet_msg = " There are no games today with the hashtag(s) provided. The list of games today are " + schedule
                api.update_status("@" + x.user.screen_name + tweet_msg, x.id)
                print("tweeted back that the hashtag did not match todays game list")
                c.execute("INSERT INTO user_id (twitterID) VALUES (" + str(x.id) + ")")
                conn.commit()
                print("mention id " + str(x.id))
                tweeted_back = True
            counter += 1

  
  
teams_dict = create_team_list()
daily_games = daily_game_list(teams_dict)
current_date = datetime.datetime.now(pytz.timezone('US/Pacific')).strftime('%Y-%m-%d')

while True:
    conn = sqlite3.connect('twitter_id.db')
    check_date = datetime.datetime.now(pytz.timezone('US/Pacific')).strftime('%Y-%m-%d')
    #if current date is different then checked date then change the todays game list and update current date.
    if (current_date != check_date):
        print("Date has changed updating games list")
        daily_games = daily_game_list(teams_dict)
        current_date = datetime.datetime.now(pytz.timezone('US/Pacific')).strftime('%Y-%m-%d')

    tweet(daily_games)
    conn.close()
    time.sleep(15)
