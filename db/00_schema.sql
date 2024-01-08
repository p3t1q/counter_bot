-- SETTINGS
ALTER DATABASE postgres
SET TIMEZONE TO "Europe/Prague";

-- TABLES
-- author id 0 for self
CREATE TABLE "counters" (
    id SERIAL PRIMARY KEY,
    label VARCHAR NOT NULL,
    author BIGINT NOT NULL,
    daily BIGINT DEFAULT 0,
    is_public BOOLEAN DEFAULT FALSE
);

CREATE TABLE "counter_updates" (
    id SERIAL PRIMARY KEY,
    counter_id BIGINT NOT NULL,
    author BIGINT NOT NULL,
    amount BIGINT NOT NULL,
    created timestamp DEFAULT current_timestamp,
    
   CONSTRAINT fk_counter_id
      FOREIGN KEY(counter_id) 
	  REFERENCES counters(id)
      ON DELETE CASCADE
)
