import logging
import socket

LOG = logging.getLogger(__name__)


class GQRXError(Exception):
    pass


class CommandError(GQRXError):
    pass


class TimeoutError(GQRXError):
    pass


class LostConnectionError(GQRXError):
    pass


class GQRX:
    def __init__(self, host='localhost', port=7356):
        self.host = host
        self.port = port
        self.tries = 2

    def connect(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.settimeout(1)
        self.s.connect((self.host, self.port))
        ver = self.get_version()
        LOG.info('connected to gqrx: %s', ver)

    def send_command_raw(self, cmd, *args):
        if args:
            args = ' '.join(str(arg) for arg in args)
            cmd = ' '.join([cmd, args])

        LOG.debug('sending command: %s', repr(cmd))
        try:
            self.s.send(cmd.encode('ascii'))
            self.s.send(b'\n')
        except (ConnectionError, BrokenPipeError):
            raise LostConnectionError()

    def read_line(self):
        buf = []
        while True:
            c = self.s.recv(1)
            if c == b'\n':
                break
            buf.append(c)

        return b''.join(buf).decode('ascii')

    def send_command(self, cmd, *args, tries=None, lines=1):
        if tries is None:
            tries = self.tries

        for i in range(tries):
            LOG.debug('command %s, try %d', cmd, i)
            res = []
            try:
                self.send_command_raw(cmd, *args)
                for j in range(lines):
                    line = self.read_line()
                    LOG.debug('line %d: %s', j, repr(line))
                    if line == 'RPRT 1':
                        raise CommandError(cmd)
                    elif line == 'RPRT 0':
                        continue

                    res.append(line)
                break
            except socket.timeout:
                pass
        else:
            raise TimeoutError()

        return res

    def get_version(self):
        res = self.send_command('_', tries=2)
        if not res[0].lower().startswith('gqrx'):
            raise ValueError('unexpected response from server: %s', res[0])

        return res[0]

    def get_freq(self):
        res = self.send_command('f')
        return int(res[0])/1000000

    def set_freq(self, f):
        f = '{}'.format(int(f*1000000))
        return self.send_command('F', f)

    def get_mod(self):
        return self.send_command('m', lines=2)

    def set_mod(self, mod):
        return self.send_command('M', mod)

    def get_signal_strength(self):
        return self.send_command('l STRENGTH')[0]

    def get_squelch(self):
        return float(self.send_command('l SQL')[0])

    def set_squelch(self, level):
        self.send_command('L SQL', level)

    def start_recording(self):
        self.send_command('AOS')

    def stop_recording(self):
        self.send_command('LOS')

    def get_recording_status(self):
        return int(self.send_command('u RECORD')[0])

    def close(self):
        self.send_command_raw('q')
        self.s.close()

    open = connect


if __name__ == '__main__':
    logging.basicConfig(level='DEBUG')
    c = GQRX()
    c.connect()
