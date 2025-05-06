from flask import Flask, render_template, request, redirect
from pymongo import MongoClient

app = Flask(__name__)

client = MongoClient("mongodb+srv://devrimotlu:faHFjntdTvDvq6t@cluster0.pjhxzsq.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client["game-db"]
games_collection = db["games"]
users_collection = db["users"]

@app.route('/')
def home():
    games = list(games_collection.find().sort("rating", -1))
    users = list(users_collection.find())
    return render_template("home.html", games=games, users=users)

@app.route('/add_game', methods=['POST'])
def add_game():
    game = {
        "name": request.form["name"],
        "genres": request.form.get("genres").split(","),
        "photo": request.form["photo"],
        "play_time": 0,
        "rating": 0,
        "all_comments": [],
        "allow_comments": True, 
        "allow_ratings": True,  
        "optional": {
            "developer": request.form.get("developer", ""),
            "release_date": request.form.get("release_date", "")
        }
    }
    games_collection.insert_one(game)
    return redirect('/')

@app.route('/add_user', methods=['POST'])
def add_user():
    user_name = request.form['user_name']
    if users_collection.find_one({"name": user_name}):
        return "This user already exists."
    new_user = {
        "name": user_name,
        "total_play_time": 0,
        "avg_rating": 0,
        "most_played_game": None,
        "comments": []
    }
    users_collection.insert_one(new_user)
    return redirect('/')

@app.route('/user/<username>')
def user_page(username):
    user = users_collection.find_one({"name": username})
    if not user:
        return f"The user didnt find: {username}"
    games = list(games_collection.find()) 
    return render_template("user.html", user=user, games=games)


@app.route('/play_game', methods=['POST'])
def play_game():
    username = request.form['username']
    game_name = request.form['game_name']
    hours = int(request.form['hours'])

    user = users_collection.find_one({"name": username})
    game = games_collection.find_one({"name": game_name})

    if not user or not game:
        return "Game or User didn't find"

    new_total = user.get("total_play_time", 0) + hours
    played = user.get("played", {})
    played[game_name] = played.get(game_name, 0) + hours
    most_played_game = max(played, key=played.get)

    users_collection.update_one(
        {"name": username},
        {"$set": {
            "total_play_time": new_total,
            "played": played,
            "most_played_game": most_played_game
        }}
    )

    new_game_playtime = game.get("play_time", 0) + hours
    games_collection.update_one(
        {"name": game_name},
        {"$set": {"play_time": new_game_playtime}}
    )

    return redirect(f"/user/{username}")
    
@app.route('/add_comment', methods=['POST'])
def add_comment():
    username = request.form['username']
    game_name = request.form['game_name']
    comment_text = request.form['comment']

    user = users_collection.find_one({"name": username})
    game = games_collection.find_one({"name": game_name})

    if not user or not game:
        return "User or Game didn't find."

    user_comment = {"game": game_name, "text": comment_text}
    users_collection.update_one(
        {"name": username},
        {"$push": {"comments": user_comment}}
    )

    game_comment = {"user": username, "text": comment_text}
    games_collection.update_one(
        {"name": game_name},
        {"$push": {"all_comments": game_comment}}
    )

    return redirect(f"/user/{username}")
@app.route('/rate_game', methods=['POST'])
def rate_game():
    username = request.form['username']
    game_name = request.form['game_name']
    score = int(request.form['score'])

    if score < 1 or score > 5:
        return "Puan 1 ile 5 arasında olmalı."

    user = users_collection.find_one({"name": {"$regex": f"^{username}$", "$options": "i"}})
    game = games_collection.find_one({"name": {"$regex": f"^{game_name}$", "$options": "i"}})

    if not user or not game:
        return "User or Game didn't find."

    
    new_rating = {"game": game_name, "score": score}
    users_collection.update_one(
        {"name": user["name"]},
        {"$push": {"ratings": new_rating}}
    )

    
    all_users = users_collection.find({"ratings.game": game_name})
    total_play = 0
    total_weighted = 0

    for u in all_users:
        played_time = u.get("played", {}).get(game_name, 0)
        for r in u.get("ratings", []):
            if r["game"].lower() == game_name.lower():
                total_play += played_time
                total_weighted += played_time * r["score"]

    avg_rating = round(total_weighted / total_play, 2) if total_play else 0

    games_collection.update_one(
        {"name": game["name"]},
        {"$set": {"rating": avg_rating}}
    )

    return redirect(f"/user/{user['name']}")

@app.route('/delete_game', methods=['POST'])
def delete_game():
    game_name = request.form['game_name']

   
    games_collection.delete_one({"name": game_name})

    
    users_collection.update_many(
        {},
        {
            "$pull": {
                "comments": {"game": game_name},
                "ratings": {"game": game_name}
            },
            "$unset": {
                f"played.{game_name}": ""  
            }
        }
    )

    return redirect('/')

    return redirect('/')
@app.route('/delete_user', methods=['POST'])
def delete_user():
    username = request.form['username']
    users_collection.delete_one({"name": username})
    return redirect('/')
@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('q', '').strip()

    if not query:
        return redirect('/')

    
    user = users_collection.find_one({"name": {"$regex": f"^{query}$", "$options": "i"}})
    if user:
        return redirect(f"/user/{user['name']}")

   
    game = games_collection.find_one({"name": {"$regex": f"^{query}$", "$options": "i"}})
    if game:
        return render_template("home.html", games=[game], users=list(users_collection.find()))

    return f"'{query}' No users or games found matching your query."
@app.route('/browse_games')
def browse_games():
    games = list(games_collection.find())
    return render_template("browse_games.html", games=games)
import os
...

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)

if __name__ == '__main__':
    app.run(debug=True)





