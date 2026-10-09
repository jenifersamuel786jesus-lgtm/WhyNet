def diagnose(results, high_latency_ms=250):
    by = {r.get('test_type'): r for r in results}
    findings = []
    def add(category, severity, symptom, evidence, causes, steps, confidence):
        findings.append({'category':category,'severity':severity,'symptom':symptom,'evidence':evidence,'likely_causes':causes,'recommendations':steps,'confidence':confidence})
    conn, dns, tcp, lat = by.get('connectivity'), by.get('dns'), by.get('tcp'), by.get('latency')
    if conn and conn.get('status') == 'offline':
        add('internet_connectivity_failure','critical','The app host could not establish its configured outbound connectivity check.',[f"Connectivity check to {conn.get('target')} failed.",conn.get('error','')],['Outbound network restriction','Target or route unavailable','Transient timeout'],['Repeat the test; compare with another authorized target.','Check outbound firewall and hosting-network policy.'],'medium')
    if dns and dns.get('status') == 'failed' and conn and conn.get('status') == 'online':
        add('dns_resolution_failure','warning','DNS resolution failed while the independent IP-based connectivity check succeeded.',[f"DNS lookup for {dns.get('target')} failed.",f"TCP connectivity to {conn.get('target')} succeeded."],['Resolver configuration or resolver outage','Domain-specific DNS issue'],['Retry the lookup.','Compare with a trusted resolver and inspect DNS settings of the hosting environment.'],'strong')
    elif dns and dns.get('status') == 'failed':
        add('dns_resolution_failure','warning','A DNS lookup failed; independent evidence is insufficient to isolate DNS as the root cause.',[f"DNS lookup for {dns.get('target')} failed."],['Resolver issue','General connectivity issue','Transient lookup failure'],['Repeat DNS and connectivity checks before changing settings.'],'limited')
    if tcp and tcp.get('status') in ('failed','timeout','refused') and conn and conn.get('status') == 'online':
        add('tcp_service_unreachable','warning',f"TCP connection to {tcp.get('target')} did not succeed ({tcp.get('status')}).",[f"The connectivity target succeeded; service test was {tcp.get('status')}.",tcp.get('error','')],['Remote service down or listening on another port','Target firewall or network policy','Transient timeout'],['Verify the hostname and port with the service owner.','Check destination firewall/service health; only test authorized targets.'],'medium')
    if lat and lat.get('avg_ms') is not None and lat['avg_ms'] > high_latency_ms:
        add('high_latency','warning',f"Average TCP handshake time was {lat['avg_ms']} ms (threshold {high_latency_ms:g} ms).",[f"{lat.get('successful_attempts')} of {lat.get('attempts')} attempts succeeded."],['Long network path or congestion','Remote service delay','Shared runtime load'],['Repeat at different times and compare targets.','Treat this as an observation, not proof of a specific root cause.'],'medium')
    if lat and lat.get('packet_loss_pct') is not None and lat['packet_loss_pct'] > 0:
        add('possible_packet_loss','warning',f"{lat['packet_loss_pct']}% of bounded TCP timing attempts failed.",[f"{lat.get('successful_attempts')} of {lat.get('attempts')} TCP attempts completed."],['Intermittent routing or service availability','Firewall rate limiting','Transient timeouts'],['Repeat with a larger time interval.','TCP failures are not equivalent to ICMP packet loss.'],'limited')
    if conn and conn.get('status') == 'online' and lat and lat.get('successful_attempts',0) < lat.get('attempts',0):
        add('intermittent_connectivity','warning','Some repeated TCP attempts failed while at least one connectivity check succeeded.',[f"{lat.get('successful_attempts')} of {lat.get('attempts')} timing attempts succeeded."],['Intermittent route/service behavior','Transient congestion or timeout'],['Repeat the bounded test and compare results over time.'],'limited')
    if not findings:
        add('insufficient_evidence','info','No fault is confirmed by the available test results.',[f"Collected {len(results)} test result(s)."],['The tested targets may not represent the affected service','Some networks block or prioritize probes'],['Run the complete suite and confirm targets are relevant.','Remember measurements describe the application host, not each visitor’s device.'],'limited')
    return findings
