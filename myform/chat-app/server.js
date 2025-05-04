const express = require('express');
const http = require('http');
const socketIo = require('socket.io');
const path = require('path');

// Initialize express app
const app = express();
const server = http.createServer(app);
const io = socketIo(server);

// Serve static files from the public directory
app.use(express.static(path.join(__dirname, 'public')));

// Serve the index.html file
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'chat-app.html'));
});

// Keep track of connected users
const users = {};
// Keep track of emails in use
const emails = new Set();
// Keep track of active private chats
const privateChats = new Map();
// Keep track of pending video call requests
const pendingVideoCalls = new Map();

// Socket.io connection handler
io.on('connection', (socket) => {
  console.log('New user connected:', socket.id);
  
  // Check if email is available
  socket.on('check email', (email) => {
    const isAvailable = !emails.has(email);
    socket.emit('email check result', { isAvailable });
  });
  
  // Handle user join
  socket.on('user join', (userData) => {
    const { username, email } = userData;
    
    if (emails.has(email)) {
      socket.emit('email check result', { isAvailable: false });
      return;
    }
    
    console.log(`${username} (${email}) joined the chat`);
    
    users[socket.id] = { 
      username, 
      email,
      socketId: socket.id
    };
    
    emails.add(email);
    
    socket.broadcast.emit('user join', { 
      username,
      socketId: socket.id
    });
    
    const onlineUsers = Object.values(users).map(user => ({
      username: user.username,
      socketId: user.socketId
    }));
    
    io.emit('online users', onlineUsers);
  });
  
  // Handle chat messages
  socket.on('chat message', (data) => {
    console.log(`Message from ${data.username}: ${data.text}`);
    
    // Broadcast the message to all users
    io.emit('chat message', {
      username: data.username,
      text: data.text,
      type: 'text'
    });
  });

  // Handle private chat request
  socket.on('private chat request', (data) => {
    const targetSocket = io.sockets.sockets.get(data.target);
    if (targetSocket) {
      targetSocket.emit('private chat request', {
        from: socket.id,
        fromUsername: users[socket.id].username
      });
    }
  });

  // Handle private chat acceptance
  socket.on('private chat accept', (data) => {
    const chatId = [socket.id, data.target].sort().join('-');
    privateChats.set(chatId, {
      participants: [socket.id, data.target],
      messages: []
    });
    
    // Notify both users that private chat is established
    io.to(socket.id).to(data.target).emit('private chat established', {
      chatId,
      participants: [socket.id, data.target]
    });
  });

  // Handle private chat messages
  socket.on('private message', (data) => {
    const chatId = data.chatId;
    const chat = privateChats.get(chatId);
    
    if (chat && chat.participants.includes(socket.id)) {
      const message = {
        from: socket.id,
        fromUsername: users[socket.id].username,
        text: data.text,
        timestamp: new Date()
      };
      
      chat.messages.push(message);
      
      // Send message to all participants in the private chat
      chat.participants.forEach(participantId => {
        io.to(participantId).emit('private message', {
          ...message,
          chatId
        });
      });
    }
  });

  // Handle private chat leave
  socket.on('private chat leave', (data) => {
    const chatId = data.chatId;
    const chat = privateChats.get(chatId);
    
    if (chat && chat.participants.includes(socket.id)) {
      // Notify other participant
      chat.participants.forEach(participantId => {
        if (participantId !== socket.id) {
          io.to(participantId).emit('private chat ended', { chatId });
        }
      });
      
      // Remove chat if it's empty
      if (chat.participants.length <= 1) {
        privateChats.delete(chatId);
      } else {
        // Remove the leaving participant
        chat.participants = chat.participants.filter(id => id !== socket.id);
      }
    }
  });

  // Handle video call request
  socket.on('video call request', (data) => {
    const targetSocket = io.sockets.sockets.get(data.target);
    if (targetSocket) {
      const requestId = `${socket.id}-${data.target}`;
      pendingVideoCalls.set(requestId, {
        from: socket.id,
        fromUsername: users[socket.id].username,
        to: data.target,
        timestamp: new Date()
      });
      
      targetSocket.emit('video call request', {
        from: socket.id,
        fromUsername: users[socket.id].username,
        requestId
      });
    }
  });

  // Handle video call response
  socket.on('video call response', (data) => {
    const { requestId, accepted } = data;
    const callRequest = pendingVideoCalls.get(requestId);
    
    if (callRequest) {
      if (accepted) {
        // Notify both users that call is accepted
        io.to(callRequest.from).to(callRequest.to).emit('video call accepted', {
          requestId,
          participants: [callRequest.from, callRequest.to]
        });
      } else {
        // Notify caller that call was rejected
        io.to(callRequest.from).emit('video call rejected', {
          requestId,
          by: socket.id
        });
      }
      pendingVideoCalls.delete(requestId);
    }
  });
  
  // WebRTC signaling (only after call is accepted)
  socket.on('call offer', (data) => {
    const targetSocket = io.sockets.sockets.get(data.target);
    if (targetSocket) {
      console.log(`Call offer from ${socket.id} to ${data.target}`);
      targetSocket.emit('call offer', data);
    }
  });
  
  socket.on('call answer', (data) => {
    const targetSocket = io.sockets.sockets.get(data.target);
    if (targetSocket) {
      console.log(`Call answer from ${socket.id} to ${data.target}`);
      targetSocket.emit('call answer', data);
    }
  });
  
  socket.on('ice candidate', (data) => {
    const targetSocket = io.sockets.sockets.get(data.target);
    if (targetSocket) {
      targetSocket.emit('ice candidate', data);
    }
  });
  
  socket.on('end call', (data) => {
    const targetSocket = io.sockets.sockets.get(data.target);
    if (targetSocket) {
      console.log(`Call ended between ${socket.id} and ${data.target}`);
      targetSocket.emit('end call', data);
    }
  });
  
  // Handle disconnection
  socket.on('disconnect', () => {
    const userData = users[socket.id];
    if (userData) {
      console.log(`${userData.username} left the chat`);
      
      // Clean up private chats
      for (const [chatId, chat] of privateChats.entries()) {
        if (chat.participants.includes(socket.id)) {
          chat.participants.forEach(participantId => {
            if (participantId !== socket.id) {
              io.to(participantId).emit('private chat ended', { chatId });
            }
          });
          privateChats.delete(chatId);
        }
      }
      
      // Clean up pending video calls
      for (const [requestId, call] of pendingVideoCalls.entries()) {
        if (call.from === socket.id || call.to === socket.id) {
          const otherUser = call.from === socket.id ? call.to : call.from;
          io.to(otherUser).emit('video call cancelled', { requestId });
          pendingVideoCalls.delete(requestId);
        }
      }
      
      socket.broadcast.emit('user leave', {
        username: userData.username,
        socketId: socket.id
      });
      
      emails.delete(userData.email);
      delete users[socket.id];
      
      const onlineUsers = Object.values(users).map(user => ({
        username: user.username,
        socketId: user.socketId
      }));
      
      io.emit('online users', onlineUsers);
    }
  });

  // Handle file messages
  socket.on('file message', (data) => {
    const { type, data: fileData, filename, isPrivate, chatId } = data;
    
    if (isPrivate) {
      // Handle private file message
      const chat = privateChats.get(chatId);
      if (chat && chat.participants.includes(socket.id)) {
        const message = {
          from: socket.id,
          fromUsername: users[socket.id].username,
          type: type,
          data: fileData,
          filename: filename,
          timestamp: new Date()
        };
        
        chat.messages.push(message);
        
        // Send to all participants in the private chat
        chat.participants.forEach(participantId => {
          io.to(participantId).emit('private message', {
            ...message,
            chatId
          });
        });
      }
    } else {
      // Handle public file message
      const message = {
        username: users[socket.id].username,
        type: type,
        data: fileData,
        filename: filename
      };
      
      io.emit('chat message', message);
    }
  });
});

// Start the server
const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});