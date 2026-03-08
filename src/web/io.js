/**
 * Socket.IO singleton - avoids circular imports between server.js and API routers.
 */
let _io = null;

export function setIo(io) {
  _io = io;
}

export function getIo() {
  return _io;
}
