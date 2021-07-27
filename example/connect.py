import asyncio
import logging
import platform
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

from pysesameos2.ble import CHBleManager
from pysesameos2.device import CHDeviceKey
from pysesameos2.helper import CHProductModel

if TYPE_CHECKING:
    from pysesameos2.device import CHSesameLock

# In order to understand the details of pysesameos2,
# here we dare to show the detailed logs.
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("bleak").setLevel(level=logging.INFO)
logger = logging.getLogger(__name__)


# https://gist.github.com/delivrance/675a4295ce7dc70f0ce0b164fcdbd798
async def ainput(prompt: str) -> str:
    with ThreadPoolExecutor(1, "AsyncInput") as executor:
        return await asyncio.get_event_loop().run_in_executor(executor, input, prompt)


def on_sesame_statechanged(device: "CHSesameLock") -> None:
    mech_status = device.getMechStatus()
    device_status = device.getDeviceStatus()

    print("=" * 10)
    print("Device status is updated!")
    print("UUID: {}".format(device.getDeviceUUID()))
    print("Product Model: {}".format(device.productModel))
    print("Device status: {}".format(device_status))

    """
    Note that even if `getDeviceStatus` succeeds, `getMechStatus` may return `None`.

    The reason is that `DeviceStatus` is a state transition of the device,
    and it always exists, regardless of the connection status with the device.
    https://doc.candyhouse.co/ja/flow_charts#sesame-%E7%8A%B6%E6%85%8B%E9%81%B7%E7%A7%BB%E5%9B%B3

    `getMechStatus` can be retrieved after the connection to the device is
    successfully established.
    """
    if mech_status is not None:
        print("Battery: {}%".format(mech_status.getBatteryPrecentage()))
        print("Battery: {:.2f}V".format(mech_status.getBatteryVoltage()))
        print("isInLockRange: {}".format(mech_status.isInLockRange()))
        print("isInUnlockRange: {}".format(mech_status.isInUnlockRange()))
        if device.productModel == CHProductModel.SS2:
            print("Position: {}".format(mech_status.getPosition()))
        elif device.productModel == CHProductModel.SesameBot1:
            print("Motor Status: {}".format(mech_status.getMotorStatus()))
    print("=" * 10)


async def connect(scan_duration: int = 15):
    """
    Let's try to make something similar to the sample script in pysesame3.
    https://github.com/mochipon/pysesame3/blob/main/docs/usage.md

    The appearance of a BLE UUID is completely different between Linux and
    macOS environments even if the device is the same. (What's about Windows??)
    """
    your_ble_uuid = (
        "24:71:89:cc:09:05"
        if platform.system() != "Darwin"
        else "B9EA5233-37EF-4DD6-87A8-2A875E821C46"
    )

    """
    Scan your device and make an instance.

    You may get an error here, but it's usually due to an incomplete
    or broken scan result.
    Please run the program as close to the SESAME device as possible
    and do the appropriate error handling (like try-except).
    """
    device = await CHBleManager().scan_by_address(
        ble_device_identifier=your_ble_uuid, scan_duration=scan_duration
    )

    """
    By decoding the QR code generated by the official iOS/Android app,
    you can get the information you need.
    https://sesame-qr-reader.vercel.app/
    """
    your_key = CHDeviceKey()
    your_key.setSecretKey("THIS_IS_YOUR_SECRET_KEY")
    your_key.setSesame2PublicKey("THIS_IS_YOUR_PUB_KEY")
    device.setKey(your_key)

    """
    Connect your device and start the session.

    The authentication process for devices proceeds asynchronously.
    Please refer to the official documentation for the state transitions.

    Before running `connect()`, `device.getDeviceStatus()` should return
    `receivedBle` as it actually received the beacon in `scan_by_address()`.

    https://doc.candyhouse.co/ja/flow_charts#sesame-%E7%8A%B6%E6%85%8B%E9%81%B7%E7%A7%BB%E5%9B%B3
    """
    print(device.getDeviceStatus())
    device.setDeviceStatusCallback(on_sesame_statechanged)
    await device.connect()

    """
    At the moment `connect()` is executed (i.e. when this line is being processed),
    the authentication process may not be completed because the process is going on
    asynchronously.

    As the name implies, `wait_for_login` is a useful feature that blocks the process
    until the login process is completed.
    You can check `getDeviceStatus()` to make sure the process completion, instead.
    """
    await device.wait_for_login()

    print("=" * 10)
    print("[Initial MechStatus]")
    print((str(device.getMechStatus())))

    print("=" * 10)
    print("[Prompt]")
    while True:
        val = await ainput("Action [lock/unlock/toggle/click]: ")

        if device.productModel == CHProductModel.SS2:
            if val == "lock":
                await device.lock(history_tag="My Script")
            elif val == "unlock":
                await device.unlock(history_tag="日本語もOK")
            elif val == "toggle":
                await device.toggle(history_tag="My Script")

        if device.productModel == CHProductModel.SesameBot1:
            if val == "click":
                await device.click(history_tag="日本語もOK")

        continue


if __name__ == "__main__":
    asyncio.run(connect())
