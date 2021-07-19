import asyncssh, asyncio, subprocess, logging
from mcconnect.errors import *

class Connection:
    """This class can be used to establish a connection to a host machine and launch a Minecraft Server (or any server actually) on it.\n
    The class provides many utilities such as checking if the host is awake, waking it up, starting the server, sending a command to it and watching for output if neccessary.\n
    \n
    The wakeCommand argument needs to contain a command that by some means causes the host to boot up and then waits until that process is completed. If it completed successfully, it should output exit state 0, if not some other value.\n
    If provided, the pingCommand needs to be a command that checks if the host is awake and returns exit code 0 if it is.
    """
    def __init__(self,hostIP : str,username : str, password : str,launchCommand : str,wakeCommand : str,shutdownCommand : str,*,port : int = 22,disableHostKeyChecking=False,pingCommand = "ping {ip} -c 1"):
        self.sshAddress = (hostIP,port)
        self.wakeCommand = wakeCommand
        self.shutdownCommand = shutdownCommand
        self.launchCommand = launchCommand

        self.disableHostKeyChecking = disableHostKeyChecking
        self.username = username
        self.password = password

        self.sshConn : asyncssh.SSHClientConnection = None
        self.serverProcess : asyncssh.SSHClientProcess = None

        self.PING_CMD = pingCommand
        pass

    async def isAwake(self):
        """Checks if the host is currently awake (read: running)\n
        This function is a coroutine\n
        """
        process : asyncio.Process = await asyncio.create_subprocess_shell(self.PING_CMD.fromat(ip=self.sshAddress[0]),stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        returncode = await process.wait()
        return returncode == 0
        pass

    async def wakeUp(self):
        """Wakes up (read: boots) the host.\n
        Returns the status code of the self.wakeCommand specified when creating the Connection object.\n
        This function is a couroutine.\n
        """
        process : asyncio.Process = await asyncio.create_subprocess_shell(self.wakeCommand.format(host=self.sshAddress[0]))
        
        return await process.wait()
        pass

    async def connect(self):
        """Creates a new asyncssh.SSHClientConnection with the host.\n
        Returns the new connection (and sets self.sshConn)\n
        Note: This will not work if the host isn't awake.\n
        This function is a couroutine\n
        """
        if self.disableHostKeyChecking:
            connection = await asyncssh.connect(self.sshAddress[0],self.sshAddress[1],username=self.username,password=self.password,known_hosts=None)
        else:
            connection = await asyncssh.connect(self.sshAddress[0],self.sshAddress[1],username=self.username,password=self.password)
        
        self.sshConn = connection
        return self.sshConn
        

    async def wake(self):
        """Combines self.wakeUp and self.connect.\n
        Return the new connection\n
        Raises WakeError if the wake script did not return status code 0\n
        This function is a coroutine
        """
        wakeSuccess = 0#await self.wakeUp()
        if wakeSuccess != 0:
            raise WakeError(f"Wake Up could not complete correctly; exited with status code {wakeSuccess}")
            return wakeSuccess
        
        return await self.connect()
        pass

    async def start(self):
        """Starts the server with self.launchCommand\n
        Returns the asyncssh.SSHClientProcess\n
        Note: This wil not work if the host is not awake or doesn't have a live connection
        """
        if self.sshConn == None:
            raise ConnectionError("SSH Connection never established; self.sshConn was None")
            return
        self.serverProcess = await self.sshConn.create_process("")
        self.writeCommand(self.launchCommand)
        return self.serverProcess
        pass

    def writeCommand(self,command : str):
        """Sends a command to the host server.\n
        Raises a CommandError if the process is closing.
        """
        if self.serverProcess.stdin.is_closing():
            raise CommandError("Process is in closing process")
        self.serverProcess.stdin.write((command + "\n"))
        logging.info(command)
        pass


    async def processWatcher(self,process : asyncssh.SSHClientProcess):
        """Looks at any data the process receives.
        """
        while True:
            try:
                line = await process.stdout.readline()
                if line!="":
                    logging.info(str(("SERVER: "+line).encode("utf-8")))
                await asyncio.sleep(0)
                pass
            except asyncio.CancelledError:
                break
        process.stdin.write_eof()
        process.stdin.close()
        process.close()
        logging.info("Watcher has reached EOF")
        pass