export const Loading = ({ label="Loading verified data…" }: {label?:string}) => <div className="state"><span className="spinner" />{label}</div>;
export const Empty = ({ title, text }: {title:string;text:string}) => <div className="empty"><b>{title}</b><p>{text}</p></div>;
export const ErrorNotice = ({ message }: {message:string}) => <div role="alert" className="notice error">{message}</div>;
