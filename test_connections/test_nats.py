import asyncio
from nats.aio.client import Client as NATS


async def run(loop):
    nc = NATS()

    await nc.connect("192.168.0.104:4222", loop=loop)

    async def message_handler(msg):
        subject = msg.subject
        reply = msg.reply
        data = msg.data
        # print("Received a message on '{subject} {reply}': {data}".format(
        #     subject=subject, reply=reply, data=data))
        print((msg.data[0] * 256 + msg.data[1])*0.3515625)
        # print(msg.data[1])

    # Simple publisher and async subscriber via coroutine.
    sid = await nc.subscribe("Encoder", cb=message_handler)

    # Stop receiving after 2 messages.
    # await nc.auto_unsubscribe(sid, 2)
    await nc.publish("Check", b'enturn:1')


    # await nc.publish("Check", b'enturn:3')
    # await nc.publish("Check", b'enturn:3')
    # await nc.publish("Check", b'enturn:3')

    # await nc.publish("Check", b'World')
    # await nc.publish("Check", b'!!!!!')


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run(loop))
    loop.run_forever()
    # loop.close()
