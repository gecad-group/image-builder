import io
import os
import time
import zipfile
import subprocess
import streamlit as st


def get_dockerfile(file):
    if file is None:
        return ""
    else:
        with zipfile.ZipFile(io.BytesIO(file.read())) as z:
            for name in z.namelist():
                if name.endswith("Dockerfile"):
                    return z.read(name).decode("UTF-8")

    return ""

def textinput_cleaner(value):
    return value.strip().replace(" ", "_").replace("/", "_").replace("\\", "_")

st.write("# Docker Imager")

st.text_input("Enter your id", key="id", max_chars=5)

file = st.file_uploader("Upload file", type="zip", disabled=st.session_state.id is None or len(st.session_state.id) < 5)

st.text_input("Project name", key="project_name", disabled=file is None, value=textinput_cleaner(file.name.rsplit(".", 1)[0] if file is not None else ""))

col1, col2 = st.columns([3, 1])

with col1:
    st.text_area("Dockerfile:", key="dockerfile", disabled=st.session_state.id is None or len(st.session_state.id) < 5 or file is None, value=get_dockerfile(file))

with col2:
    st.write("Build for:")
    st.checkbox("PC", value=True, key="amd64_build", disabled=file is None)
    st.checkbox("Raspberry Pi", key="arm64_build", disabled=file is None)


if st.button("Build image", disabled=st.session_state.id is None or len(st.session_state.id) < 5 or file is None):
    with st.status("Building image...", expanded=True) as status:
        # Unzip the file to /tmp/<id>-<project>
        projectName = f"{textinput_cleaner(st.session_state.id)}-{textinput_cleaner(st.session_state.project_name)}"
        projectPath = f"/tmp/{projectName}"

        with st.spinner("Unzipping project..."):
            # reset file pointer
            file.seek(0)
            with zipfile.ZipFile(io.BytesIO(file.read())) as z:
                z.extractall(projectPath)

        # Overwrite the Dockerfile
        with open(f"{projectPath}/Dockerfile", "w") as f:
            f.write(st.session_state.dockerfile)

        st.success("Project unzipped")

        with st.spinner("Building..."):
            build_targets = ",".join([target for target, flag in zip(["linux/amd64", "linux/arm64"], [st.session_state.amd64_build, st.session_state.arm64_build]) if flag])
            build = subprocess.run(f"docker buildx build --platform {build_targets} -t {projectName.lower()} {projectPath}", shell=True, universal_newlines=True, capture_output=True)
            history = subprocess.run(f"docker image history {projectName.lower()}", shell=True, universal_newlines=True, capture_output=True)
        st.success("Image built")
        # Why does it output to stderr? Spent more time than needed trying to understand what was going on
        st.text_area("Build Log", value=build.stderr, disabled=True)
        # And then history to stdout... Make it make sense
        st.text_area("Image History", value=history.stdout, disabled=True)

        # Clean up
        with st.spinner("Cleaning up..."):
            os.system(f"rm -rf {projectPath}")
        st.success("Cleaned up build artifacts")