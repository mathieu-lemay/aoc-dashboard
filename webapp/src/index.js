import React from 'react';
import ReactDOM from 'react-dom';
import configData from "./config.json";
import './index.css';

class Member extends React.Component {
    render() {
        return (
        <tr>
            <td>{this.props.pos}</td>
            <td>{this.props.name}</td>
            <td>{this.props.stars}</td>
            <td>{this.props.goldStars}</td>
            <td>{this.props.silverStars}</td>
            <td>{this.props.drawEntries}</td>
        </tr>
        );
    }
}

class Stars extends React.Component {
    render() {
        let elements = [];
        for (let i=0; i<25; i++) {
            let s = this.props.values[i];

            let cls = "star-none";
            if (s === 2) {
                cls = "star-both";
            } else if (s === 1) {
                cls = "star-one";
            }

            elements.push(<span className={cls}>*</span>);
        }

        return elements;
    }
}

class StadingsGrid extends React.Component {
    render() {
        let members = [];
        Object.entries(this.props.standings).forEach(([k, v]) => {
            members.push(
                <Member
                    key={k}
                    pos={v.position}
                    name={v.name}
                    stars=<Stars values={v.stars} />
                    goldStars={v.gold_stars}
                    silverStars={v.silver_stars}
                    drawEntries={v.draw_entries}
                />
            );
        });
        members.sort((a, b) => a.props.pos - b.props.pos);

        return (
            <table>
                <thead>
                    <tr>
                        <th>Pos.</th>
                        <th>Name</th>
                        <th>Stars</th>
                        <th>Gold Stars</th>
                        <th>Silver Stars</th>
                        <th>Draw Entries</th>
                    </tr>
                </thead>
                <tbody>
                    {members}
                </tbody>
            </table>
        );
    }
}

class Dashboard extends React.Component {
    constructor(props) {
        super(props);

        this.state = {
            year: props.year,
            standings: {},
            timestamp: null,
            ready: false,
        };
    }

    componentDidMount() {
        const { year } = this.state;

        fetch(configData.SERVER_URL + "/standings/" + year)
        .then(response => response.json())
        .then(response => {
            this.setState({standings: response.standings, timestamp: response.timestamp, ready: true});
        })
        .catch(err => {
            console.log(err);
        });
    }

    render() {
        const { year, standings, timestamp, ready } = this.state;

        if (!ready) {
            return (
                <div className="dashboard">
                    <h1 className="title">Advent of Code - {year}</h1>
                </div>
            );
        }

        return (
            <div className="dashboard">
                <h1 className="title">Advent of Code - {year}</h1>
                <StadingsGrid standings={standings} />
                <div className="last-update">Last update: {
                    new Intl.DateTimeFormat("sv", {
                        dateStyle: 'short', timeStyle: 'long',
                    }).format(convertUTCDateToLocalDate(timestamp))
                }</div>
            </div>
        );
    }
}

function convertUTCDateToLocalDate(date) {
  var dateLocal = new Date(date);
  return new Date(dateLocal.getTime() - dateLocal.getTimezoneOffset() * 60 * 1000);
}

// ========================================

ReactDOM.render(
  <Dashboard year="2021" />,
  document.getElementById('root')
);
