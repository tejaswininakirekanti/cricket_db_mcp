-- queries to create tables
CREATE TABLE teams (
    team_id     SERIAL PRIMARY KEY,
    team_name   VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE players (
    player_id   SERIAL PRIMARY KEY,
    player_name VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE matches (
    match_id        SERIAL PRIMARY KEY,
    season          SMALLINT      NOT NULL,
    match_date      DATE          NOT NULL,
    city            VARCHAR(80),
    venue           VARCHAR(120),
    match_number    SMALLINT,
    match_type      VARCHAR(30),
    team1           INT NOT NULL REFERENCES teams(team_id),
    team2           INT NOT NULL REFERENCES teams(team_id),
    toss_winner     INT           REFERENCES teams(team_id),
    toss_decision   VARCHAR(10),                 
    match_winner          INT           REFERENCES teams(team_id),
    win_by_runs     SMALLINT,
    win_by_wkts     SMALLINT,
    player_of_match INT           REFERENCES players(player_id)
);

CREATE TABLE innings (
    match_id     INT      NOT NULL REFERENCES matches(match_id)
                 ON DELETE CASCADE,
    innings_no   SMALLINT NOT NULL CHECK (innings_no BETWEEN 1 AND 2),
    batting_team INT      NOT NULL REFERENCES teams(team_id),
    runs         SMALLINT,
    wickets      SMALLINT,
    overs        DECIMAL(4,1),          
    PRIMARY KEY (match_id, innings_no)
);

CREATE TABLE deliveries (
    delivery_id     BIGSERIAL PRIMARY KEY,
    match_id        INT      NOT NULL REFERENCES matches(match_id)
                             ON DELETE CASCADE,
    innings_no      SMALLINT NOT NULL,
    over_no         SMALLINT NOT NULL,   
    ball_no         SMALLINT NOT NULL,   
    batting_team    INT      NOT NULL REFERENCES teams(team_id),
    bowling_team    INT      NOT NULL REFERENCES teams(team_id),
    batter_id       INT      NOT NULL REFERENCES players(player_id),
    bowler_id       INT      NOT NULL REFERENCES players(player_id),
    non_striker_id  INT      NOT NULL REFERENCES players(player_id),
    runs_batter     SMALLINT DEFAULT 0,
    runs_extras     SMALLINT DEFAULT 0,
    wicket_type     VARCHAR(20),        
    player_out_id   INT REFERENCES players(player_id),
    fielder_id      INT REFERENCES players(player_id),
    UNIQUE (match_id, innings_no, over_no, ball_no)
);

CREATE TABLE powerplays (
    match_id    INT      NOT NULL REFERENCES matches(match_id)
                         ON DELETE CASCADE,
    innings_no  SMALLINT NOT NULL,
    pp_type     VARCHAR(30),            
    from_over   SMALLINT,
    to_over     SMALLINT,
    PRIMARY KEY (match_id, innings_no, pp_type)
);