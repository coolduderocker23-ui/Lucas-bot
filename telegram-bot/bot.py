import asyncio
import io
import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import aiohttp
from telethon import TelegramClient, events
from telethon.tl.types import MessageEntityTextUrl, MessageMediaPhoto, MessageMediaDocument
API_ID   = 38541705
API_HASH = "f4ab5fc207f625ab6c348e572b971684"
SOURCE_CHANNEL = "testacb12"
# Add as many channels/groups as you want here
YOUR_CHANNELS = ["AllChinaBuy08", "AcbFinds"]
MY_REFS = {
    "acbuy":   "D3D8WL",
    "mulebuy": "201073119",
    "usfans":  "JWYXFG",
    "hoobuy":  "YEw0km8D",
}
URL_PATTERN = re.compile(r"https?://[^\s\]>)\"']+", re.IGNORECASE)
def get_platform(url):
    try:
        domain = urlparse(url).netloc.lower().replace("www.", "")
        if "link.acbuy.com" in domain or domain == "acbuy.com": return "acbuy"
        if "mulebuy.com" in domain: return "mulebuy"
        if "usfans.com" in domain: return "usfans"
        if "hoobuy.cc" in domain or "hoobuy.com" in domain: return "hoobuy"
    except: pass
    return None
def is_short_link(url):
    domain = urlparse(url).netloc.lower()
    return "link.acbuy.com" in domain or "hoobuy.cc" in domain
def set_ref_param(url, ref):
    try:
        parsed = urlparse(url)
        params = parse_qs(parsed.query, keep_blank_values=True)
        params["ref"] = [ref]
        new_query = urlencode({k: v[0] if len(v)==1 else v for k,v in params.items()}, doseq=True)
        return urlunparse(parsed._replace(query=new_query))
    except: return url
async def expand_url(url):
    for method in ("HEAD", "GET"):
        try:
            async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as s:
                req = s.head if method == "HEAD" else s.get
                async with req(url, allow_redirects=True, timeout=aiohttp.ClientTimeout(total=6)) as r:
                    final = str(r.url)
                    if final and final != url: return final
        except: continue
    return url
async def swap_link(url):
    platform = get_platform(url)
    if not platform: return url
    my_ref = MY_REFS[platform]
    if is_short_link(url):
        expanded = await expand_url(url)
        return set_ref_param(expanded, my_ref)
    return set_ref_param(url, my_ref)
async def replace_affiliate_links(text):
    if not text: return text
    seen, urls = set(), []
    for u in URL_PATTERN.findall(text):
        if u not in seen:
            seen.add(u); urls.append(u)
    result = text
    for original_url in urls:
        new_url = await swap_link(original_url)
        if new_url != original_url:
            result = result.replace(original_url, new_url)
    return result
async def process_entities(entities):
    if not entities: return entities, False
    changed = False
    updated = []
    for entity in entities:
        if isinstance(entity, MessageEntityTextUrl):
            new_url = await swap_link(entity.url)
            if new_url != entity.url:
                changed = True
                entity = MessageEntityTextUrl(offset=entity.offset, length=entity.length, url=new_url)
        updated.append(entity)
    return updated, changed
client = TelegramClient("session", API_ID, API_HASH)
@client.on(events.Album(chats=SOURCE_CHANNEL))
async def album_handler(event):
    caption = ""
    caption_entities = None
    for msg in event.messages:
        if msg.message:
            caption = msg.message
            caption_entities = msg.entities
            break
    modified_caption = await replace_affiliate_links(caption)
    modified_entities, entity_changed = await process_entities(caption_entities)
    links_changed = (modified_caption != caption) or entity_changed
    try:
        files = []
        for msg in event.messages:
            if msg.media:
                data = await client.download_media(msg.media, file=bytes)
                if data:
                    if isinstance(msg.media, MessageMediaPhoto):
                        ext = ".jpg"
                    elif isinstance(msg.media, MessageMediaDocument):
                        mime = getattr(msg.media.document, "mime_type", "image/jpeg")
                        ext = "." + mime.split("/")[-1].replace("jpeg", "jpg")
                    else:
                        ext = ".jpg"
                    buf = io.BytesIO(data)
                    buf.name = f"photo{ext}"
                    files.append(buf)
        if files:
            for ch in YOUR_CHANNELS:
                await client.send_file(ch, files, caption=modified_caption or None, formatting_entities=modified_entities or None)
            tag = "🔗 links swapped" if links_changed else "no links"
            print(f'✅ Album cloned ({len(files)} photos) | {tag}')
    except Exception as e:
        print(f"❌ Album error: {e}")
@client.on(events.NewMessage(chats=SOURCE_CHANNEL))
async def handler(event):
    msg = event.message
    if msg.grouped_id: return
    original_text = msg.message or ""
    modified_text = await replace_affiliate_links(original_text)
    modified_entities, entity_changed = await process_entities(msg.entities)
    links_changed = (modified_text != original_text) or entity_changed
    try:
        if msg.media:
            for ch in YOUR_CHANNELS:
                await client.send_file(ch, msg.media, caption=modified_text or None, formatting_entities=modified_entities or None)
        elif modified_text:
            for ch in YOUR_CHANNELS:
                await client.send_message(ch, modified_text, formatting_entities=modified_entities or None)
        else: return
        tag = "🔗 links swapped" if links_changed else "no links"
        print(f'✅ Cloned | {tag} | "{modified_text[:70]}"')
    except Exception as e:
        print(f"❌ Error: {e}")
async def main():
    print("🔥 Telegram Channel Cloner running")
    print(f"📥 Watching : @{SOURCE_CHANNEL}")
    print(f"📤 Posting  : {YOUR_CHANNELS}")
    print("Listening… press Ctrl+C to stop\n")
    await client.run_until_disconnected()
with client:
    client.loop.run_until_complete(main())