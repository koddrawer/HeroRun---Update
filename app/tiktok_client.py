# Kết nối TikTok LIVE (thư viện TikTokLive) — chạy trong luồng riêng, đẩy sự kiện vào hàng đợi
import asyncio, threading, time


def _first(*vals):
    for v in vals:
        if v: return v
    return None


def user_info(u):
    if u is None:
        return {'uid': 'anon', 'name': 'Ẩn danh', 'avatar': None}
    uid = _first(getattr(u, 'display_id', None), getattr(u, 'unique_id', None),
                 getattr(u, 'id_str', None), str(getattr(u, 'id', '') or ''), 'anon')
    name = _first(getattr(u, 'nickname', None), getattr(u, 'nick_name', None), uid)
    avatar = None
    for attr in ('avatar_thumb', 'avatar_medium', 'avatar_large', 'avatar_jpg'):
        img = getattr(u, attr, None)
        if img is None: continue
        urls = _first(getattr(img, 'url_list', None), getattr(img, 'm_urls', None), getattr(img, 'urls', None))
        if urls:
            avatar = list(urls)[0]; break
    return {'uid': str(uid), 'name': str(name), 'avatar': avatar}


class TikTokThread:
    def __init__(self, inbox, log):
        self.inbox = inbox
        self.log = log
        self.client = None
        self.loop = None
        self.thread = None
        self.status = 'Chưa kết nối'
        self.username = ''
        self.want = False
        self.gen = 0

    def connect(self, username, sign_key=''):
        self.disconnect()
        username = username.strip().lstrip('@')
        if not username:
            self.status = 'Thiếu tên TikTok'; return
        self.username = username
        self.want = True
        self.gen += 1
        self.thread = threading.Thread(target=self._run, args=(username, sign_key, self.gen), daemon=True)
        self.thread.start()

    def disconnect(self):
        self.want = False
        if self.client and self.loop and self.loop.is_running():
            try:
                asyncio.run_coroutine_threadsafe(self.client.disconnect(), self.loop)
            except Exception:
                pass
        self.status = 'Đã ngắt'

    def _run(self, username, sign_key, gen):
        try:
            from TikTokLive import TikTokLiveClient
            from TikTokLive.events import (ConnectEvent, DisconnectEvent, CommentEvent, GiftEvent,
                                           LikeEvent, JoinEvent, FollowEvent, ShareEvent)
        except Exception as e:
            self.status = 'Thiếu thư viện TikTokLive'
            self.log(f'Lỗi import TikTokLive: {e}')
            return
        if sign_key:
            try:
                from TikTokLive.client.web.web_settings import WebDefaults
                WebDefaults.tiktok_sign_api_key = sign_key
            except Exception:
                pass
        alive = lambda: self.want and self.gen == gen
        while alive():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            client = TikTokLiveClient(unique_id='@' + username)
            self.client = client
            push = self.inbox.put

            @client.on(ConnectEvent)
            async def _c(ev):
                self.status = f'Đã kết nối @{username}'
                self.log(self.status)

            @client.on(DisconnectEvent)
            async def _d(ev):
                self.status = 'Mất kết nối'
                self.log('Mất kết nối TikTok')

            @client.on(JoinEvent)
            async def _j(ev):
                push(('tt', dict(type='join', **user_info(ev.user))))

            @client.on(CommentEvent)
            async def _cm(ev):
                push(('tt', dict(type='comment', text=getattr(ev, 'comment', '') or '', **user_info(ev.user))))

            @client.on(LikeEvent)
            async def _l(ev):
                push(('tt', dict(type='like', count=int(getattr(ev, 'count', 1) or 1), **user_info(ev.user))))

            @client.on(FollowEvent)
            async def _f(ev):
                push(('tt', dict(type='follow', **user_info(ev.user))))

            @client.on(ShareEvent)
            async def _s(ev):
                push(('tt', dict(type='share', **user_info(ev.user))))

            @client.on(GiftEvent)
            async def _g(ev):
                gift = getattr(ev, 'gift', None)
                if gift is None: return
                if getattr(ev, 'streaking', False):
                    return  # chờ kết thúc combo
                unit = int(getattr(gift, 'diamond_count', 0) or 0)
                cnt = int(getattr(ev, 'repeat_count', 1) or 1)
                push(('tt', dict(type='gift', unit=unit, count=cnt,
                                 gift=str(getattr(gift, 'name', '') or ''), **user_info(ev.user))))

            self.status = f'Đang kết nối @{username}...'
            try:
                # connect() chạy tới khi mất kết nối / bị ngắt
                self.loop.run_until_complete(client.connect())
            except Exception as e:
                self.status = f'Lỗi: {str(e)[:80]}'
                self.log(f'TikTok lỗi: {e}')
            try:
                self.loop.run_until_complete(client.disconnect())
            except Exception:
                pass
            try:
                self.loop.close()
            except Exception:
                pass
            if alive():
                self.log('Thử kết nối lại sau 10s...')
                for _ in range(10):
                    if not alive(): break
                    time.sleep(1)
        if self.gen == gen: self.client = None
