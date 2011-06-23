
DROP TABLE raw;
CREATE TABLE raw (
	id serial primary key,
	insert_time timestamp with time zone DEFAULT NOW(),
	flow_start timestamp with time zone,
	flow_finish timestamp with time zone,
	agent inet,
	src_ip inet,
	dst_ip inet,
	protocol integer,
	src_port integer,
	dst_port integer,
	packets integer,
	octets integer,
	peer_src_as integer,
	peer_dst_as integer,
	ifindex_in integer,
	ifindex_out integer,
	if_in integer,
	if_out integer,
	src_as integer,
	dst_as integer,
	src_aspath text,
	dst_aspath text,
	sampling_interval integer
) TABLESPACE ssd2;

CREATE INDEX raw__flow_finish__idx ON raw (flow_finish);
CREATE INDEX raw__agent__idx ON raw (agent);

GRANT USAGE ON raw_id_seq TO flowd;
GRANT SELECT ON raw_id_seq TO flowd ;
GRANT INSERT ON raw TO flowd;
GRANT SELECT ON raw TO flowd ;



