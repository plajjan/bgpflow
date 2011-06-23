
CREATE OR REPLACE FUNCTION flow_as_summarize() RETURNS boolean AS $_$
DECLARE
	start_time timestamp with time zone;
	stop_time timestamp with time zone;
BEGIN
	stop_time := date_trunc('minute',now()) - (extract(minute from now())::integer % 5) * interval '1 minute';
	start_time := stop_time - 5 * interval '1 minute';

	INSERT INTO flow_as_5min (time, node, ifindex_in, ifindex_out, if_type_in, if_type_out, peer_src_as, peer_dst_as, src_as, dst_as, src_aspath, dst_aspath, packets, bytes) 
	SELECT	date_trunc('minute', flow_finish) - (extract(minute from flow_finish)::integer % 5) * interval '1 minute'AS time,
			agent AS node,
			ifindex_in,
			ifindex_out,
			if_in AS if_type_in,
			if_out AS if_type_out,
			peer_src_as,
			peer_dst_as,
			src_as,
			dst_as,
			src_aspath,
			dst_aspath,
			SUM(packets)*1024 AS packets,
			SUM(octets)*1024 AS bytes
		FROM raw
		WHERE 
			flow_finish > start_time
			AND flow_finish < stop_time
		GROUP BY time, agent, ifindex_in, ifindex_out, if_in, if_out, peer_src_as, peer_dst_as, src_as, dst_as, src_aspath, dst_aspath;

	RETURN true;
END;
$_$ LANGUAGE plpgsql;
