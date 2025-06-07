# Command list for resonite headless app

## saveConfig

  Saves the current settings into the original config file
  Usage: saveconfig <filename> (optional, will save in place without)

## login

  Login to an account
  Usage: login <username/email> <password>

## logout

  Log out from the current account
  Usage: logout

## message

  Message user in friends list
  Usage: message <friend name> <message>
  Example:
    ```shell
    TWC Debug - do not join>message TWC-Test-User1 "Test message"
    SIGNALR: SendMessage - Id: MSG-2fc37ac0-8e99-44de-a2a7-1ab1ae0098f4, OwnerId: U-1diPwgYpBhY, RecipientId: U-1e0baHzIF4i, SenderId: U-1diPwgYpBhY, Type: Text
    Message sent!
    ```

## invite

  Invite a friend to the currently focused world
  Usage: invite <friend name>
  Example:
    ```shell
    TWC Debug - do not join>invite TWC-Test-User1
    Updated: 01/01/0001 00:00:00 -> 07/06/2025 14:25:53
    Updated:  -> TWC Debug - do not join
    Updated:  -> Instance to test out headless management interface
    Updated:  -> S-87fe7d8f-6571-4c6a-938b-21c0757afab8
    Updated: Private -> RegisteredUsers
    Updated: False -> True
    Updated: 0 -> 5
    Updated:  -> U-1diPwgYpBhY
    Updated:  -> ad8f0e9c-4051-4c2c-8db8-f2d520239d32
    Updated:  -> TWC-Headless-Bot
    Updated:  -> du7zuugh11mh1kha6kne6c1qfybha6ms41i6e3p5fcbca8as6g5y
    Updated: False -> True
    Updated:  -> https://skyfrost-archive.resonite.com/thumbnails/72802320-f872-4005-ab64-0f036521c198.webp
    SIGNALR: SendMessage - Id: MSG-65ebc6b6-4ead-4ea4-bfac-59841500e35e, OwnerId: U-1diPwgYpBhY, RecipientId: U-1e0baHzIF4i, SenderId: U-1diPwgYpBhY, Type: SessionInvite
    SIGNALR: BroadcastSession SessionInfo. Id: S-87fe7d8f-6571-4c6a-938b-21c0757afab8, Name: TWC Debug - do not join, Host: TWC-Headless-Bot, CorrespondingWorldId: , URLs: lnl-nat://6a95325a-dbe2-4397-afda-f735285b5000/S-87fe7d8f-6571-4c6a-938b-21c0757afab8, IsExpired: False to Public
    Invite sent!
    ```

## friendRequests

  Lists all incoming friend requests
  Usage: friendrequests
  Example:
    ```shell
    TWC Debug - do not join>friendRequests
    TWC-Test-User1
    ```

## acceptFriendRequest

  Accepts a friend request
  Usage: acceptfriendrequest <friend name>
  Example:
    ```shell
    TWC Debug - do not join>acceptfriendrequest TWC-Test-User1
    Request accepted!
    ```

## worlds

  Lists all active worlds
  Usage: worlds
  Example:
    ```shell
    TWC Debug - do not join>worlds
    [0] TWC Debug - do not join         Users: 2    Present: 1      AccessLevel: RegisteredUsers    MaxUsers: 6
    ```

## focus

  Focus world
  Usage: focus <world name or number>

## startWorldURL

  Start a new world from URL
  Usage: startworldurl <record URL>

## startWorldTemplate

  Start a new world from template
  Usage: startworldtemplate <template name>

## status

  Shows the status of the current world
  Usage: status
  Example:
    ```shell
    TWC Debug - do not join>status
    Name: TWC Debug - do not join
    SessionID: S-87fe7d8f-6571-4c6a-938b-21c0757afab8
    Current Users: 1
    Present Users: 0
    Max Users: 6
    Uptime: 01:12:35.4423964
    Access Level: RegisteredUsers
    Hidden from listing: False
    Mobile Friendly: False
    Description: Instance to test out headless management interface
    Tags: debug, test, TheWorldCore
    Users: TWC-Headless-Bot
    ```

## sessionUrl

  Prints the URL of the current session
  Usage: sessionurl
  Example:
    ```shell
    TWC Debug - do not join>sessionurl
    https://go.resonite.com/session/S-87fe7d8f-6571-4c6a-938b-21c0757afab8
    ```

## sessionID

  Prints the ID of the current session
  Usage: sessionid
  Example:
    ```shell
    TWC Debug - do not join>sessionid
    S-87fe7d8f-6571-4c6a-938b-21c0757afab8
    ```

## copySessionURL

  Copies the URL of the current session to clipboard
  Usage: copysessionurl

## copySessionID

  Copies the ID of the current session to clipboard
  Usage: copysessionid

## users

  Lists all users in the world
  Usage: users
  Example:
    ```shell
    TWC Debug - do not join>users
    TWC-Headless-Bot        ID: U-1diPwgYpBhY       Role: Admin     Present: False  Ping: 0 ms      FPS: 60.00322   Silenced: False
    TWC-Test-User1  ID: U-1e0baHzIF4i       Role: Builder   Present: True   Ping: 0 ms      FPS: 59.999996  Silenced: False
    ```

## close

  Closes the currently focused world
  Usage: close

## save

  Saves the currently focused world
  Usage: save

## restart

  Restarts the current world
  Usage: restart

## kick

  Kicks given user from the session
  Usage: kick <username>
  Example:
    ```shell
    TWC Debug - do not join>kick TWC-Test-User1
    KickRequest: True for User ID3632F00 (Alloc: 1) - UserName: TWC-Test-User1, UserId: U-1e0baHzIF4i, MachineId: 66m********bmy, Role: Guest. Changing User: , ScheduledForValidation: True

    <Sometimes error text here see example in ban section>
    TWC-Test-User1 kicked!
    ```

## silence

  Silences given user in the session
  Usage: silence <username>
  Example:
    ```shell
    TWC Debug - do not join>silence TWC-Test-User1
    Silence: True for User ID417D100 (Alloc: 1) - UserName: TWC-Test-User1, UserId: U-1e0baHzIF4i, MachineId: 66*********bmy, Role: Guest. Changing User: 

    <Sometimes error text here see example in ban section>
    TWC-Test-User1 silenced!
    ```

## unsilence

  Removes silence from given user in the session
  Usage: unsilence <username>
  Example:
    ```shell
    TWC Debug - do not join>unsilence TWC-Test-User1
    Silence: False for User ID417D100 (Alloc: 1) - UserName: TWC-Test-User1, UserId: U-1e0baHzIF4i, MachineId: 66***bmy, Role: Guest. Changing User: User ID2E00 (Alloc: 0) - UserName: TWC-Headless-Bot, UserId: U-1diPwgYpBhY, MachineId: du***g5y, Role: Admin

    <Sometimes error text here see example in ban section>
    TWC-Test-User1 unsilenced!
    ```

## ban

  Bans the user from all sessions hosted by this server
  Usage: ban <username>
  Example:
    ```shell
    TWC Debug - do not join>ban TWC-Test-User1
    BanRequest: True for User ID296C700 (Alloc: 1) - UserName: TWC-Test-User1, UserId: U-1e0baHzIF4i, MachineId: 66*****bbmy, Role: Guest. Changing User: , ScheduledForValidation: True

    at System.Environment.get_StackTrace()
    at Elements.Core.UniLog.Log(String message, Boolean stackTrace) in D:\Workspace\Everion\FrooxEngine\Elements.Core\UniLog.cs:line 36
    at FrooxEngine.User.BanRequest_OnValueChange(SyncField`1 syncField)
    at FrooxEngine.User.Ban()
    at FrooxEngine.Headless.HeadlessCommands.<>c.<SetupCommonCommands>b__0_23(User u, List`1 args) in D:\Workspace\Everion\FrooxEngine\Headless\Commands\HeadlessCommands.cs:line 415
    at FrooxEngine.Headless.UserCommand.<>c__DisplayClass0_0.<.ctor>b__0(World world, List`1 args) in D:\Workspace\Everion\FrooxEngine\Headless\Commands\UserCommand.cs:line 46
    at FrooxEngine.Headless.WorldCommand.<>c__DisplayClass22_0.<.ctor>b__0(World world, List`1 args) in D:\Workspace\Everion\FrooxEngine\Headless\Commands\WorldCommand.cs:line 50
    at FrooxEngine.Headless.WorldCommand.<>c__DisplayClass23_0.<<Invoke>b__0>d.MoveNext() in D:\Workspace\Everion\FrooxEngine\Headless\Commands\WorldCommand.cs:line 77
    at System.Runtime.CompilerServices.AsyncTaskMethodBuilder`1.AsyncStateMachineBox`1.ExecutionContextCallback(Object s)
    at System.Threading.ExecutionContext.RunInternal(ExecutionContext executionContext, ContextCallback callback, Object state)
    at System.Runtime.CompilerServices.AsyncTaskMethodBuilder`1.AsyncStateMachineBox`1.MoveNext(Thread threadPoolThread)
    at System.Runtime.CompilerServices.AsyncTaskMethodBuilder`1.AsyncStateMachineBox`1.MoveNext()
    at FrooxEngine.NextUpdate.<>c__DisplayClass3_0.<OnCompleted>b__0(Object u)
    at FrooxEngine.CoroutineManager.ExecuteAsyncQueue(SpinQueue`1 queue)
    at FrooxEngine.CoroutineManager.ExecuteWorldQueue(Double deltaTime)
    at FrooxEngine.World.RefreshStep()
    at FrooxEngine.World.Refresh()
    at FrooxEngine.WorldManager.UpdateStep()
    at FrooxEngine.WorldManager.RunUpdateLoop()
    at FrooxEngine.Engine.UpdateStep()
    at FrooxEngine.Engine.RunUpdateLoop()
    at FrooxEngine.StandaloneFrooxEngineRunner.UpdateLoop()
    TWC-Test-User1 banned!
    Banning user User ID296C700 (Alloc: 1) - UserName: TWC-Test-User1, UserId: U-1e0baHzIF4i, MachineId: 66*****************bbmy, Role: Guest. Last Changing User: 
    ```

## unban

  Removes ban for user with given username
  Usage: unban <username>
  Example:
    ```shell
    TWC Debug - do not join>unban TWC-Test-User1
    Removed 1 matching bans
    ```

## listbans

  Lists all active bans
  Usage: listbans
  example:
    ```shell
    TWC Debug - do not join>listbans
    [0]     Username: TWC-Test-User1        UserID: U-1e0baHzIF4i   MachineIds: 668************bbmy
    ```

## banByName

  Bans user with given username from all sessions hosted by this server
  Usage: banbyname <username>

## unbanByName

  Unbans user with the given username from all sessions hosted by this server
  Usage: unbanbyname <username>

## banByID

  Bans user with given User ID from all sessions hosted by this server
  Usage: banbyid <user ID>

## unbanByID

  Unbans user with given User ID from all sessions hosted by this server
  Usage: unbanbyid <user ID>

## respawn

  Respawns given user
  Usage: respawn <username>
  Example
    ```shell
    TWC Debug - do not join>respawn TWC-Test-User1
    Destroying User: User ID4CC3C00 (Alloc: 1) - UserName: TWC-Test-User1, UserId: U-1e0baHzIF4i, MachineId: 66******bmy, Role: Builder
    Currently updating user: User ID2E00 (Alloc: 0) - UserName: TWC-Headless-Bot, UserId: U-1diPwgYpBhY, MachineId: du****6g5y, Role: Admin

    <Sometimes error text here see example in ban section>
    TWC-Test-User1 respawned!
    ```

## role

  Assigns a role to given user
  Usage: role <username> <role>
  Example:
    ```shell
    TWC Debug - do not join>role TWC-Test-User1 builder
    TWC-Test-User1 now has role Builder!
    ```

## name

  Sets a new world name
  Usage: name <new name>

## accessLevel

  Sets a new world access level
  Usage: accesslevel <access level name>

## hideFromListing

  Sets whether the session should be hidden from listing or not
  Usage: hidefromlisting <true/false>

## description

  Sets a new world description
  Usage: description <new description>

## maxUsers

  Sets user limit
  Usage: maxusers <max users>

## awayKickInterval

  Sets the away kick interval
  Usage: awaykickinterval <interval in minutes>

## import

  Import an asset into the focused world
  Usage: import <file path or URL>

## importMinecraft

  Import a Minecraft world. Requires Mineways to be installed.
  Usage: importminecraft <folder containing Minecraft world with the level.dat file>

## dynamicImpulse

  Sends a dynamic impulse with given tag to the scene root
  Usage: dynamicimpulse <tag>

## dynamicImpulseString

  Sends a dynamic impulse with given tag and string value to the scene root
  Usage: dynamicimpulsestring <tag> <value>

## dynamicImpulseInt

  Sends a dynamic impulse with given tag and integer value to the scene root
  Usage: dynamicimpulseint <tag> <value>

## dynamicImpulseFloat

  Sends a dynamic impulse with given tag and float value to the scene root
  Usage: dynamicimpulsefloat <tag> <value>

## spawn

  Spawns an item from a record URL into the world's root
  Usage: spawn <url> <active> <persistent>

## gc

  Forces full garbage collection
  Usage: gc
  Example:
    ```shell
    TWC Debug - do not join>gc
    GC finished
    ```

## debugWorldState

  Prints out diagnostic information for all worlds which can be used for debugging purposes
  Usage: debugworldstate
  Example:
    ```shell
    TWC Debug - do not join>debugWorldState
    World: Userspace, Handle: 1
      WorldStage: RefreshBegin
      SyncTick: 1
      WorldSessionState:
      WorldSessionStopProcessing:
      WorldMessagesToProcess:
      WorldTotalProcessedMessages:
      WorldMessagesToTransmit:
      ProcessingSyncMessage:
      CurrentlyDecodingStream:
    World: TWC Debug - do not join, Handle: 2
      WorldStage: RefreshBegin
      SyncTick: 191540
      WorldSessionState: WaitingForSyncThreadEvent
      WorldSessionStopProcessing: False
      WorldMessagesToProcess: 0
      WorldTotalProcessedMessages: 128420
      WorldMessagesToTransmit: 0
      ProcessingSyncMessage:
      CurrentlyDecodingStream:
    ```

## shutdown

  Shuts down the headless client
  Usage: shutdown

## tickRate

  Sets the maximum simulation rate for the servers
  Usage: tickrate <ticks per second>

## log

  Switches the interactive shell to logging output. Press enter again to restore interactive.
  Usage: log
