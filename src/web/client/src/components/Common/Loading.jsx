function Loading({ message = "読み込み中..." }) {
  return (
    <div className="loading">
      <div className="loading-spinner"></div>
      <p className="loading-message">{message}</p>
    </div>
  );
}

export default Loading;
