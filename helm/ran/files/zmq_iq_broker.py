#!/usr/bin/env python3
"""Fan out one DU downlink and sum UE uplinks onto a single ZMQ radio.

srsRAN and OCUDU ZMQ radios publish raw complex64 IQ on tx_port and subscribe
on rx_port. This process sits between one DU and several UEs: every downlink
frame is copied to each UE, and the uplink sent back to the DU is the sum of
the matching uplink frames. A UE that has not produced a frame of the same
length contributes zeros so the DU clock still advances.
"""

import argparse
import array


COMPLEX64_BYTES = 8


def sum_uplink(downlink, uplink_frames):
    """Return a complex64 sum the same length as the downlink frame.

    Frames that are missing or a different length are skipped. The result is
    then all zeros, which is the zero-fill path for a UE that is not up yet.
    """
    length = len(downlink)
    if length == 0 or length % COMPLEX64_BYTES != 0:
        return b"\x00" * length

    sample_count = length // COMPLEX64_BYTES
    total_i = [0.0] * sample_count
    total_q = [0.0] * sample_count
    for frame in uplink_frames:
        if frame is None or len(frame) != length:
            continue
        samples = array.array("f")
        samples.frombytes(frame)
        for index in range(sample_count):
            total_i[index] += samples[2 * index]
            total_q[index] += samples[2 * index + 1]

    summed = array.array("f")
    for index in range(sample_count):
        summed.append(total_i[index])
        summed.append(total_q[index])
    return summed.tobytes()


def copy_downlink(downlink, ue_count):
    """Return one identical downlink payload per UE."""
    return [bytes(downlink) for _ in range(ue_count)]


def _parse_ue(value):
    host, ul_port, dl_port = value.split(":")
    return host, int(ul_port), int(dl_port)


def _run(du_tx, du_rx_bind, ues):
    import zmq

    context = zmq.Context()
    du_sub = context.socket(zmq.SUB)
    du_sub.setsockopt(zmq.SUBSCRIBE, b"")
    du_sub.connect(du_tx)

    du_pub = context.socket(zmq.PUB)
    du_pub.bind(du_rx_bind)

    ue_pubs = []
    ue_subs = []
    for host, ul_port, dl_port in ues:
        pub = context.socket(zmq.PUB)
        pub.bind("tcp://0.0.0.0:{0}".format(dl_port))
        ue_pubs.append(pub)
        sub = context.socket(zmq.SUB)
        sub.setsockopt(zmq.SUBSCRIBE, b"")
        sub.connect("tcp://{0}:{1}".format(host, ul_port))
        ue_subs.append(sub)

    print(
        "zmq-iq-broker: du_tx={0} du_rx_bind={1} ues={2}".format(
            du_tx, du_rx_bind, ues
        ),
        flush=True,
    )
    try:
        while True:
            downlink = du_sub.recv()
            for pub, payload in zip(ue_pubs, copy_downlink(downlink, len(ue_pubs))):
                pub.send(payload)
            uplinks = []
            for sub in ue_subs:
                frame = None
                while True:
                    try:
                        frame = sub.recv(flags=zmq.NOBLOCK)
                    except zmq.Again:
                        break
                uplinks.append(frame)
            du_pub.send(sum_uplink(downlink, uplinks))
    finally:
        du_sub.close(linger=0)
        du_pub.close(linger=0)
        for sock in ue_pubs + ue_subs:
            sock.close(linger=0)
        context.term()


def main(argv=None):
    parser = argparse.ArgumentParser(description="DL-copy / UL-sum ZMQ IQ broker")
    parser.add_argument("--du-tx", required=True, help="DU PUB endpoint to subscribe")
    parser.add_argument("--du-rx-bind", required=True, help="PUB bind for the DU uplink")
    parser.add_argument(
        "--ue",
        action="append",
        required=True,
        help="UE as host:ul_port:dl_port (repeat per UE)",
    )
    args = parser.parse_args(argv)
    _run(args.du_tx, args.du_rx_bind, [_parse_ue(item) for item in args.ue])


if __name__ == "__main__":
    main()
