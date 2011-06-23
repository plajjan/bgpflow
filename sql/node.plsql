CREATE TABLE node (
	id serial PRIMARY KEY,
	fqdn varchar(256) NOT NULL
) TABLESPACE ssd;
