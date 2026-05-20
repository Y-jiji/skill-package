import * as React from "react";

interface ButtonProps {
    label: string;
}

function Button(props: ButtonProps) {
    return <button>{props.label}</button>;
}

class Modal extends React.Component<ButtonProps> {
    render() {
        return <div className="modal">{this.props.label}</div>;
    }
}

const Arrow = (p: ButtonProps) => <div>{p.label}</div>;
