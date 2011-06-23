SET default_tablespace = ssd2;

CREATE TABLE flow_as_5min (
	id bigserial UNIQUE PRIMARY KEY,
	time timestamp with time zone NOT NULL,
	node inet NOT NULL,
	ifindex_in integer,
	ifindex_out integer,
	if_type_in integer,
	if_type_out integer,
	peer_src_as integer,
	peer_dst_as integer,
	src_as integer,
	dst_as integer,
	src_aspath text,
	dst_aspath text,
	packets bigint,
	bytes bigint
) TABLESPACE ssd2;

CREATE UNIQUE INDEX flow_as_5min_unique_idx ON flow_as_5min (time, node, ifindex_in, ifindex_out, peer_src_as, peer_dst_as, src_as, dst_as, src_aspath, dst_aspath);
CREATE INDEX flow_as_5min__time__idx ON flow_as_5min (time);
CREATE INDEX flow_as_5min__node__idx ON flow_as_5min (node);
CREATE INDEX flow_as_5min__ifindex_in__idx ON flow_as_5min (ifindex_in);
CREATE INDEX flow_as_5min__ifindex_out__idx ON flow_as_5min (ifindex_out);
CREATE INDEX flow_as_5min__if_type_in__idx ON flow_as_5min (if_type_in);
CREATE INDEX flow_as_5min__if_type_out__idx ON flow_as_5min (if_type_out);
CREATE INDEX flow_as_5min__peer_src_as__idx ON flow_as_5min (peer_src_as);
CREATE INDEX flow_as_5min__peer_dst_as__idx ON flow_as_5min (peer_dst_as);
CREATE INDEX flow_as_5min__src_as__idx ON flow_as_5min (src_as);
CREATE INDEX flow_as_5min__dst_as__idx ON flow_as_5min (dst_as);
