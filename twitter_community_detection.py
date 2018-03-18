from twitter import *
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import sys
import time
from twitter.api import TwitterHTTPError
from urllib.error import URLError
from http.client import BadStatusLine



credentials_dict = {Add credentials here}






def make_twitter_request(twitter_api_func, max_errors=10, *args, **kw):
    # A nested helper function that handles common HTTPErrors. Return an updated
    # value for wait_period if the problem is a 500 level error. Block until the
    # rate limit is reset if it's a rate limiting issue (429 error). Returns None
    # for 401 and 404 errors, which requires special handling by the caller.
    def handle_twitter_http_error(e, wait_period=2, sleep_when_rate_limited=True):
        if wait_period > 3600: # Seconds
            print('Too many retries. Quitting.', file=sys.stderr)
            raise e
        if e.e.code == 401:
            return None
        elif e.e.code == 404:
            print('Encountered 404 Error (Not Found)', file=sys.stderr)
            return None
        elif e.e.code == 429:
            print('Encountered 429 Error (Rate Limit Exceeded)', file=sys.stderr)
            if sleep_when_rate_limited:
                print("Retrying in 15 minutes...ZzZ...", file=sys.stderr)
                sys.stderr.flush()
                time.sleep(60*15 + 5)
                print('...ZzZ...Awake now and trying again.', file=sys.stderr)
                return 2
            else:
                raise e # Caller must handle the rate limiting issue
        elif e.e.code in (500, 502, 503, 504):
            print('Encountered %i Error. Retrying in %i seconds' % (e.e.code, wait_period), file=sys.stderr)
            time.sleep(wait_period)
            wait_period *= 1.5
            return wait_period
        else:
            raise e

    # End of nested helper function

    wait_period = 2
    error_count = 0
    while True:
        try:
            return twitter_api_func(*args, **kw)
        except TwitterHTTPError as e:
            error_count = 0
            wait_period = handle_twitter_http_error(e, wait_period)
            if wait_period is None:
                return
        except URLError as e:
            error_count += 1
            print("URLError encountered. Continuing.", file=sys.stderr)
            if error_count > max_errors:
                print("Too many consecutive errors...bailing out.", file=sys.stderr)
                raise
        except BadStatusLine as e:
            error_count += 1
            print >> sys.stderr, "BadStatusLine encountered. Continuing."
            if error_count > max_errors:
                print("Too many consecutive errors...bailing out.", file=sys.stderr)
                raise



# This will let us create new partial
# functions with arguments set to 
# certain values.
from functools import partial

# This was maxint.
# There is no longer a maxint (in Python 3)
from sys import maxsize


def get_friends_followers_ids(twitter_api, screen_name=None, user_id=None,
                                friends_limit=maxsize, followers_limit=maxsize):
    # Must have either screen_name or user_id (logical xor)
    assert (screen_name != None) != (user_id != None), \
    "Must have screen_name or user_id, but not both"
    
    # You can also do this with a function closure.
    get_friends_ids = partial(make_twitter_request, twitter_api.friends.ids,
                                count=5000)
    get_followers_ids = partial(make_twitter_request, twitter_api.followers.ids,
                                count=5000)
    friends_ids, followers_ids = [], []
    for twitter_api_func, limit, ids, label in [
            [get_friends_ids, friends_limit, friends_ids, "friends"],
            [get_followers_ids, followers_limit, followers_ids, "followers"]
            ]:
        #LOOK HERE! This little line is important.
        if limit == 0: continue
        cursor = -1
        while cursor != 0:
            # Use make_twitter_request via the partially bound callable...
            if screen_name:
                response = twitter_api_func(screen_name=screen_name, cursor=cursor)
            else: # user_id
                response = twitter_api_func(user_id=user_id, cursor=cursor)
            if response is not None:
                ids += response['ids']
                cursor = response['next_cursor']
            print('Fetched {0} total {1} ids for {2}'.format(len(ids),
                    label, (user_id or screen_name), file=sys.stderr))
            if len(ids) >= limit or response is None:
                break
    # Do something useful with the IDs, like store them to disk...
    return friends_ids[:friends_limit], followers_ids[:followers_limit]





# Create a mostly empty data frame,
# and write it to a CSV file.
df = pd.DataFrame(columns=['ID','followers'])
df.to_csv('followers.csv', index=False)

# Our function
def save_followers(fid, followers):
    df = pd.DataFrame([[fid, followers]], columns=['ID','followers'])
    with open('followers.csv', 'a') as f:
        df.to_csv(f,header=False, index=False)


def twitter_frndship_graph():
    # followers ids list 
    # first user : 2693104332
    
    ids = [2693104332]
    
    
    # counter for number of nodes
    count_nodes = 1

    # created 4 apps(for time out issue) & cred_count changes credentiols after each 2 requests
    cred_count = 0


    for user in ids:
        #credentials changes after every 2 requests
        
        list_cred = credentials_dict[cred_count]
        t = Twitter(auth=OAuth(list_cred[0],list_cred[1],list_cred[2],list_cred[3]))

        friends_ids, followers_ids = get_friends_followers_ids(t,user_id= user, friends_limit=1000, followers_limit=1000)
        reciprocal_friends = set(friends_ids) & set(followers_ids)

#       counter to check number of nodes
        if count_nodes > 100:
            break
        
        reciprocal_dict = {}
        for id_user in reciprocal_friends:
            user_data = t.users.lookup(user_id = id_user)
            reciprocal_dict[id_user] = user_data[0]['followers_count']
            
#       sort reciprocal friends on the basis of followers count  
        list_dict = sorted(reciprocal_dict, key=reciprocal_dict.get)
        
        
        if len(list_dict) < 5:
            ids.extend(list_dict)
            save_followers(user, ','.join([str(x) for x in list_dict]))
            count_nodes = count_nodes + len(list_dict)
        else:
            updated_list = [list_dict[i] for i in (-1,-2,-3,-4,-5)]
            ids.extend(updated_list)
            save_followers(user,  ','.join([str(x) for x in updated_list]))
            count_nodes = count_nodes + 5

        if cred_count == (len(credentials_dict) - 1):
            cred_count = 0
        else:
            cred_count = cred_count + 1


# created graph from followers csv file using panda


df = pd.read_csv("followers.csv")
G = nx.Graph()
for index, row in df.iterrows():
    vertex = row['ID']
    list_followers = row['followers'].split(',')
    for follower in list_followers:
        node = int(follower)
        G.add_edge(vertex,node)


# friendship graph of twitter user 2693104332

nx.draw(G,font_weight='bold')
fig = plt.gcf()
fig.set_size_inches(22.5, 8.5)
plt.show()



a =nx.algorithms.community.kernighan_lin_bisection(G)


val_map = {}
for id in a[0]:
    val_map[id] = 1.0


# community graph of twitter user 2693104332
values = [val_map.get(node, 0.25) for node in G.nodes()]

nx.draw(G, cmap=plt.get_cmap('jet'), node_color=values)
fig = plt.gcf()
fig.set_size_inches(22.5, 8.5)
plt.show()