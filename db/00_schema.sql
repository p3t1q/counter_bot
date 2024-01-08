-- SETTINGS
ALTER DATABASE postgres
SET TIMEZONE TO "Europe/Prague";

-- TABLES
CREATE TABLE "counters" (
    id SERIAL PRIMARY KEY,
    label VARCHAR NOT NULL,
    author BIGINT NOT NULL
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
