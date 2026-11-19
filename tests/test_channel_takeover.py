"""Local HTTP regressions for pre-response channel takeover."""
from pathlib import Path
import socket
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import httpx

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests')]
from channels import ChannelRouter
from server import Gateway
from storage import ROUTER_MODEL,Settings
from test_router import MockSupplier,profile


class TakeoverTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='relay-takeover-')
        self.settings=Settings(Path(self.temp.name))
        self.primary=MockSupplier();self.backup=MockSupplier()
        self.suppliers=[self.primary,self.backup]
        self.gateway=None
        self.configure([self.primary.url,self.backup.url])
        self.choice=patch('channels.random.choices',side_effect=lambda population,**kwargs:[population[0]])
        self.choice.start()

    def tearDown(self):
        if self.gateway:self.gateway.stop()
        self.choice.stop()
        for supplier in self.suppliers:supplier.close()
        self.temp.cleanup()

    def configure(self,urls):
        current=self.settings.snapshot().get('selected')
        draft=profile(channels=[dict(label=f'channel-{i}',base_url=url,weight=1,enabled=True) for i,url in enumerate(urls)])
        if current:draft['id']=current
        self.settings.upsert(draft,'',channel_keys=[f'fixture-key-{i}' for i in range(len(urls))])

    def start(self):
        self.gateway=Gateway(self.settings,with_telemetry=False,load_activity=False)
        self.gateway.start(0)

    def post(self,*,stream=False,claude=False):
        body=(dict(model=ROUTER_MODEL,max_tokens=256,messages=[dict(role='user',content='same turn')],stream=stream)
              if claude else dict(model=ROUTER_MODEL,input='same turn',stream=stream))
        response=httpx.post(f'http://127.0.0.1:{self.gateway.port}'+('/v1/messages' if claude else '/v1/responses'),
            headers={'Authorization':'Bearer '+self.settings.local_token()},json=body,timeout=15,trust_env=False)
        deadline=time.monotonic()+2
        while not self.gateway.activity.recent(1) and time.monotonic()<deadline:time.sleep(.005)
        return response

    def assert_rescued(self,response,cause):
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(self.backup.connection_count,1)
        rows=self.gateway.activity.recent(10)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0].get('mitigated'),cause)
        self.assertTrue(rows[0]['ok'])
        self.assertIn((self.settings.selected()['id'],0),self.gateway.channel_router.cooling())
        self.assertEqual(self.backup.requests[0]['model'],'demo-model')
        content=self.backup.requests[0]['messages'][-1]['content']
        if isinstance(content,list):content=''.join(block['text'] for block in content)
        self.assertEqual(content,'same turn')

    def test_connection_refused_reaches_backup(self):
        with socket.socket() as blocked:
            blocked.bind(('127.0.0.1',0))
            self.configure([f'http://127.0.0.1:{blocked.getsockname()[1]}/v1',self.backup.url])
            self.start()
            with patch('server.TRANSPORT_RETRY_BASE_SECONDS',.01):response=self.post()
            self.assert_rescued(response,'unavailable')

    def test_connections_dropped_before_headers_reach_backup(self):
        self.primary.drop_connections=99;self.start()
        with patch('server.TRANSPORT_RETRY_BASE_SECONDS',.01):response=self.post()
        self.assert_rescued(response,'unavailable')
        self.assertEqual(self.primary.connection_count,3)

    def test_read_timeout_reserves_time_for_backup(self):
        original=self.primary.server.RequestHandlerClass
        def delayed(*args,**kwargs):
            time.sleep(1.5)
            original(*args,**kwargs)
        self.primary.server.RequestHandlerClass=delayed
        self.start();began=time.monotonic()
        with patch('server.UPSTREAM_TOTAL_BUDGET_SECONDS',2.4):response=self.post()
        self.assert_rescued(response,'timeout')
        self.assertLess(time.monotonic()-began,2.4)

    def test_connect_timeout_reaches_backup(self):
        self.start();client=self.gateway._client();original=client.stream
        def stream(method,url,**kwargs):
            if url.startswith(self.primary.url):raise httpx.ConnectTimeout('synthetic connect timeout')
            return original(method,url,**kwargs)
        with patch.object(client,'stream',side_effect=stream),patch('server.TRANSPORT_RETRY_BASE_SECONDS',.01):response=self.post()
        self.assert_rescued(response,'timeout')

    def test_rate_limit_reaches_backup(self):
        self.primary.status=429;self.primary.retry_after='0';self.start()
        self.assert_rescued(self.post(),'rate_limit')

    def test_long_retry_after_switches_provider_without_repeating_that_channel(self):
        self.primary.status=429;self.primary.retry_after='120';self.start()
        self.assert_rescued(self.post(),'rate_limit')
        self.assertEqual(self.primary.connection_count,1)

    def test_responses_stream_starts_normally_after_takeover(self):
        self.primary.status=429;self.primary.retry_after='0';self.start()
        response=self.post(stream=True)
        self.assert_rescued(response,'rate_limit')
        self.assertIn('response.completed',response.text)
        self.assertNotIn('response.failed',response.text)

    def test_claude_stream_starts_normally_after_takeover(self):
        self.primary.drop_connections=99;self.start()
        with patch('server.TRANSPORT_RETRY_BASE_SECONDS',.01):response=self.post(stream=True,claude=True)
        self.assert_rescued(response,'unavailable')
        self.assertIn('message_stop',response.text)
        self.assertNotIn('event: error',response.text)

    def test_third_channel_can_rescue_when_first_two_fail(self):
        third=MockSupplier();self.suppliers.append(third)
        self.configure([self.primary.url,self.backup.url,third.url])
        self.primary.status=429;self.primary.retry_after='0';self.backup.drop_connections=99;self.start()
        with patch('server.TRANSPORT_RETRY_BASE_SECONDS',.01):response=self.post()
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(third.connection_count,1)
        self.assertEqual(self.primary.connection_count,2)
        self.assertEqual(self.backup.connection_count,3)
        self.assertEqual(len(self.gateway.activity.recent(10)),1)
        self.assertEqual(len(self.gateway.channel_router.cooling()),2)

    def test_all_channels_fail_without_looping_back(self):
        self.primary.status=429;self.primary.retry_after='0';self.backup.drop_connections=99;self.start()
        with patch('server.TRANSPORT_RETRY_BASE_SECONDS',.01):response=self.post()
        self.assertEqual(response.status_code,503)
        self.assertEqual(self.primary.connection_count,2)
        self.assertEqual(self.backup.connection_count,3)
        self.assertFalse(self.gateway.activity.recent(1)[0].get('mitigated'))

    def test_started_stream_is_not_replayed(self):
        self.primary.truncate_stream=True;self.start()
        response=self.post(stream=True)
        self.assertEqual(response.status_code,200)
        self.assertIn('response.failed',response.text)
        self.assertEqual(self.primary.connection_count,1)
        self.assertEqual(self.backup.connection_count,0)

    def test_parameter_and_authentication_errors_do_not_switch(self):
        self.start()
        for status in (400,401,403):
            self.primary.status=status
            response=self.post()
            self.assertEqual(response.status_code,status)
        self.assertEqual(self.backup.connection_count,0)
        self.assertEqual(self.gateway.channel_router.cooling(),{})

    def test_local_concurrency_limit_is_not_a_supplier_failure(self):
        self.start()
        with patch.object(self.gateway.slots,'acquire',return_value=False):response=self.post()
        self.assertEqual(response.status_code,429)
        self.assertEqual(self.primary.connection_count,0)
        self.assertEqual(self.backup.connection_count,0)
        self.assertEqual(self.gateway.channel_router.cooling(),{})

    def test_merged_profiles_exclude_owner_and_index_together(self):
        router=ChannelRouter()
        first=dict(id='first',model='same',base_url='http://first/v1',channels=[])
        second=dict(id='second',model='same',base_url='http://second/v1',channels=[])
        group=dict(first,_group_members=[first,second])
        chosen,index=router.select(group,exclude={('first',0)})
        self.assertEqual((chosen['id'],index),('second',0))
        with self.assertRaises(ValueError):router.select(group,exclude={('first',0),('second',0)})

    def test_same_model_peer_profile_rescues_default_route(self):
        self.primary.status=429;self.primary.retry_after='0'
        self.settings=Settings(Path(self.temp.name)/'grouped')
        self.settings.upsert(profile(base_url=self.primary.url),'fixture-a')
        self.settings.upsert(profile(base_url=self.backup.url),'fixture-b')
        self.start()
        response=self.post()
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(self.backup.connection_count,1)

    def test_default_model_change_does_not_change_inflight_failover_model(self):
        other=MockSupplier();self.suppliers.append(other)
        initial=self.settings.snapshot()['selected']
        other_profile=self.settings.upsert(profile(model='other-model',base_url=other.url),'fixture-other')
        self.settings.select(initial)
        original=self.primary.server.RequestHandlerClass
        settings=self.settings
        class ChangeDefault(original):
            def do_POST(handler):
                settings.select(other_profile['id'])
                super().do_POST()
        self.primary.server.RequestHandlerClass=ChangeDefault
        self.primary.status=429;self.primary.retry_after='120';self.start()
        self.assertEqual(self.post().status_code,200)
        self.assertEqual(self.backup.connection_count,1)
        self.assertEqual(other.connection_count,0)
        self.assertEqual(self.backup.requests[0]['model'],'demo-model')

if __name__=='__main__':unittest.main()
