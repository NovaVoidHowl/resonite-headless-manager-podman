<a name="readme-top"></a>

<!-- PROJECT SHIELDS -->

<!--
*** I'm using markdown "reference style" links for readability.
*** Reference links are enclosed in brackets [ ] instead of parentheses ( ).
*** See the bottom of this document for the declaration of the reference variables
*** for contributors-url, forks-url, etc. This is an optional, concise syntax you may use.
*** https://www.markdownguide.org/basic-syntax/#reference-style-links
-->

> [!WARNING]
> This software is currently in development and not yet ready for active use

[![Contributors][contributors-shield]][contributors-url] [![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url] [![Issues][issues-shield]][issues-url]
[![MIT License][license-shield]][license-url]

<br />
<div align="center">
<h3 align="center">Resonite Headless Manager (Podman Edition)</h3>

<p align="center">
    <br />
    <a href="https://github.com/NovaVoidHowl/resonite-headless-manager-podman/issues">Report Bug</a>
    ·
    <a href="https://github.com/NovaVoidHowl/resonite-headless-manager-podman/issues">Request Feature</a>
</p>
</div>

<!-- TABLE OF CONTENTS -->

<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
    </li>
    <li>
      <a href="#Features">About The Project</a>
    </li>
    <li>
      <a href="#Installation">About The Project</a>
    </li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact-and-links">Contact and Links</a></li>
    <li><a href="#acknowledgments">Acknowledgments</a></li>
    <li><a href="#project-tools">Project tools</a></li>
  </ol>
</details>

<!-- ABOUT THE PROJECT -->

## About The Project

A web-based management interface for Resonite headless servers running in Podman containers.\
This application provides real-time monitoring and control of your Resonite worlds through an intuitive web interface.

![image](https://github.com/user-attachments/assets/ba5a5e28-639d-47bd-b133-5ba4727a91a2)

## Features

- Real-time Monitoring

  - Live container status and system resource usage
  - Active worlds overview with detailed statistics
  - Connected users monitoring with presence status
  - System CPU and memory usage tracking

- World Management

  - View and modify world properties
  - Control world visibility and access levels
  - Manage maximum user limits
  - Save, restart, or close worlds

- User Management

  - Real-time user monitoring
  - User role management
  - Kick, ban, and silence controls
  - Friend request handling
  - Ban list management

- **Server Configuration**

  - Built-in configuration editor
  - JSON validation and formatting
  - Live configuration updates

- **Console Access**

  - Direct access to server console
  - Real-time command output

## Installation

> [!TIP]
> **Prerequisites**
>
> - Python 3.13.0 +
> - Podman 5.5.0 +
> - Resonite Headless Server running in a Podman container.\
>   I personally use [this setup from ShadowPanther](https://github.com/shadowpanther/resonite-headless).

1. Clone the repository:

```bash
git clone https://github.com/NovaVoidHowl/resonite-headless-manager-podman.git
cd resonite-headless-manager
```

2. Start the app via:

```bash
./start-service.sh
```

> [!CAUTION]
> **Security Considerations**
>
> This application is designed for local network use. If exposing to the internet:
>
> - Use a reverse proxy with SSL/TLS
> - Implement proper authentication
> - Configure appropriate firewall rules

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- CONTRIBUTING -->

## Contributing

Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any
contributions you make are **appreciated**. Please see [CONTRIBUTING.md](CONTRIBUTING.md) for more details.

If you have a suggestion that would make this better, please fork the repo and create a pull request. You can also
simply open an issue with the tag "enhancement".

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

<!-- LICENSE -->

## License

MIT\
Please see [LICENSE](LICENSE) for information.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- CONTACT -->

## Contact and Links

[@NovaVoidHowl](https://novavoidhowl.uk/)

Codebase Link: [https://rhm-pm.dev.novavoidhowl.uk](https://rhm-pm.dev.novavoidhowl.uk)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- ACKNOWLEDGMENTS -->

## Acknowledgments

This project is substantially based on\
[https://github.com/Zetaphor/resonite-headless-manager](https://github.com/Zetaphor/resonite-headless-manager)

Without the above, this project would not exist!

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- PROJECT TOOLS -->

## Project tools

- VS Code, ide
- Pre-Commit, linting and error detection
- Github Copilot, Code gen + error/issue analysis

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- MARKDOWN LINKS & IMAGES -->

<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->

[contributors-shield]: https://img.shields.io/github/contributors/NovaVoidHowl/resonite-headless-manager-podman.svg?style=plastic
[contributors-url]: https://github.com/NovaVoidHowl/resonite-headless-manager-podman/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/NovaVoidHowl/resonite-headless-manager-podman.svg?style=plastic
[forks-url]: https://github.com/NovaVoidHowl/resonite-headless-manager-podman/network/members
[issues-shield]: https://img.shields.io/github/issues/NovaVoidHowl/resonite-headless-manager-podman.svg?style=plastic
[issues-url]: https://github.com/NovaVoidHowl/resonite-headless-manager-podman/issues
[license-shield]: https://img.shields.io/badge/License-MIT-blue
[license-url]: https://github.com/NovaVoidHowl/resonite-headless-manager-podman/blob/main/LICENSE
[stars-shield]: https://img.shields.io/github/stars/NovaVoidHowl/resonite-headless-manager-podman.svg?style=plastic
[stars-url]: https://github.com/NovaVoidHowl/resonite-headless-manager-podman/stargazers
