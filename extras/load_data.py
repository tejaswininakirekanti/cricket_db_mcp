import pandas as pd
import json
from pathlib import Path
import psycopg2
from psycopg2.extras import execute_batch, execute_values

# replace the place holders for database name, username and password accordingly
DSN  = "dbname=<db_name> user=<username> password=<pwd> host=127.0.0.1 port=5432"

def insert_row(cur, cache, table_name, col_name, val):
    if val in cache:
        return cache[val]
    cur.execute(
            f'''
            INSERT INTO {table_name} ({col_name})
            VALUES (%s)
            ON CONFLICT ({col_name}) DO NOTHING
        RETURNING {table_name[:-1]}_id; 
        ''',(val,),
    )
    res = cur.fetchone()
    if res:
        _id= res[0]
    else:
        cur.execute(
            f"SELECT {table_name[:-1]}_id FROM {table_name} WHERE {col_name} = %s",
            (val,),
        )
        _id = cur.fetchone()[0]

    cache[val] = _id
    return _id


def summarise_innings(inn_data):
    runs = wkts = 0
    last_over = last_ball = 0

    for over in inn_data["overs"]:
        o = over["over"]
        for d in over["deliveries"]:
            runs += d["runs"]["total"]         
            if d.get("wicket"):                
                wkts += 1
            last_over = o
    return runs, wkts, last_over

def load_deliveries(cur, rows):
    execute_values(
        cur,
        """
        INSERT INTO deliveries (
            match_id, innings_no, over_no, ball_no, batting_team, bowling_team,
            batter_id, bowler_id, non_striker_id,
            runs_batter, runs_extras, wicket_type, player_out_id, fielder_id
        )
        VALUES %s
        """,
        rows,
    )


def load_innings(cur, match_id, t1,t2, team_cache, player_cache, innings):

    for inn in innings:
        inn_no = 1 if 'target' not in inn else 2
        
        bat_team = insert_row(cur, team_cache, "teams", "team_name",
                            inn['team'])
        total, wkts, overs = summarise_innings(inn)
        cur.execute(
            """
            INSERT INTO innings (match_id, innings_no, batting_team,
                                runs, wickets, overs)
            VALUES (%s,%s,%s,%s,%s,%s);
            """,
            (
                match_id,
                inn_no,
                bat_team,
                total, wkts, overs,
            ),
        )

        #  powerplays table (optional, if present)
        if "powerplays" in inn:
            execute_values(
                cur,
                """
                INSERT INTO powerplays (match_id, innings_no, pp_type,
                                        from_over, to_over)
                VALUES %s
                ON CONFLICT DO NOTHING
                """,
                [
                    (
                        match_id,
                        inn_no,
                        pp["type"],
                        pp["from"],
                        pp["to"],
                    )
                    for pp in inn["powerplays"]
                ],
            )

        #  deliveries  insert
        rows = []
        for over_info in inn["overs"]:
            over_no = over_info["over"]
            for ball_no,ball in enumerate(over_info["deliveries"],start=1):
                batter_id = insert_row(cur, player_cache, "players", "player_name",
                                        ball["batter"])
                bowler_id = insert_row(cur, player_cache, "players", "player_name",
                                        ball["bowler"])
                ns_id = insert_row(cur, player_cache, "players", "player_name",
                                    ball["non_striker"])
                if t1 == bat_team:
                    bowling_team = t2
                else:
                    bowling_team = t1
                wicket_type = None
                fielder_name = None
                fielder_id = None
                if 'wickets' in ball:
                    wicket_type = ball['wickets'][0]['kind']
                    if "fielders" in ball["wickets"][0]:
                        fielder_name = ball["wickets"][0]["fielders"][0]['name']
                        fielder_id = insert_row(cur, player_cache, "players", "player_name", fielder_name)
                
                rows.append(
                    (
                        match_id,
                        inn_no,
                        over_no,
                        ball_no,
                        bat_team,
                        bowling_team,
                        batter_id,
                        bowler_id,
                        ns_id,
                        ball["runs"]["batter"],
                        ball["runs"]["extras"],
                        wicket_type,
                        insert_row(cur, player_cache, "players", "player_name",
                                    ball["wickets"][0]["player_out"]) if "wickets" in ball else None,

                        fielder_id,
                        
                    )
                )

    # push the rows to innings table
    if rows:
        load_deliveries(cur, rows)

def load_match(data, cur, team_cache, player_cache):

    # loading teams

    t1 = insert_row(cur, team_cache, 'teams', 'team_name', data['info']['teams'][0])
    t2 = insert_row(cur, team_cache, 'teams', 'team_name', data['info']['teams'][1])

    # loading matches table
    info = data['info']
    cur.execute(
        f'''  
        INSERT INTO matches (
            season, match_date, city, venue, match_number, match_type,
            team1, team2, toss_winner, toss_decision,
            match_winner, win_by_runs, win_by_wkts, player_of_match
        )
        VALUES (%s,%s,%s,%s,%s,%s,
                %s,%s,%s,%s,
                %s,%s,%s,
                (SELECT player_id FROM players WHERE player_name = %s))
        RETURNING match_id;
        ''',
        (
            info["season"],
            info["dates"][0],               
            info.get("city"),
            info.get("venue"),
            info["event"].get("match_number"),
            info.get("match_type"),
            t1, t2,
            insert_row(cur, team_cache, "teams", "team_name", info["toss"]["winner"]),
            info["toss"]["decision"],
            insert_row(cur, team_cache, "teams", "team_name",
                        info["outcome"].get("winner")) if info["outcome"].get("winner") else None,
            info["outcome"].get("by", {}).get("runs"),
            info["outcome"].get("by", {}).get("wickets"),
            info["player_of_match"][0] if "player_of_match" in info else None,
        ),
    )
    match_id = cur.fetchone()[0]
    # load innings
    load_innings(cur, match_id, t1, t2, team_cache, player_cache, data["innings"])

    print(f"loaded match {match_id} ")



def load_json(file):
    with file.open("r", encoding="utf-8") as fp:
        data = json.load(fp)
    team_cache, player_cache = {}, {}

    with psycopg2.connect(DSN) as conn:
        conn.autocommit = False            
        with conn.cursor() as cur:
            try:
                load_match(data, cur, team_cache, player_cache)
                conn.commit()
            except Exception as e:
                print("error occured")
                conn.rollback()


# selected list of json files to load data- can change to work for all files
files_list = ['335982','335983','335984','335985','335986']

for file_num in files_list:
    FILE = Path(f"../ipl_json/{file_num}.json")
    load_json(FILE)