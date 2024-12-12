import io
import os
import zipfile
import subprocess
import streamlit as st


REGISTRYNAME = "docker3.gecad.isep.ipp.pt"


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

st.text_input("Enter your id", key="id", max_chars=5, help="This is your unique identifier to push images to the registry. Should be the same as your ")

file = st.file_uploader("Upload file", type="zip", disabled=st.session_state.id is None or len(st.session_state.id) < 5,
                        help="The zip file should have the Dockerfile at the root and all the necessary files to build the image")

col1, col2 = st.columns([3, 1])

with col1:
    st.text_input("Project name", key="project_name", disabled=file is None, help="The image will have the same name as this. Some characters might be replaced with and underscore to avoid issues",
                  value=textinput_cleaner(file.name.rsplit(".", 1)[0] if file is not None else ""))
    st.text_area("Dockerfile:", key="dockerfile", help="You can edit the Dockerfile here before building the image",
                 disabled=st.session_state.id is None or len(st.session_state.id) < 5 or file is None, value=get_dockerfile(file))

with col2:
    st.text_input("Version Tag", key="version_tag", disabled=file is None, value="latest",
                  help="You can push multiple tags by separating them with a comma\n\nExample: `latest,v1.0`")
    st.write("Build for:")
    st.checkbox("PC", value=True, key="amd64_build", disabled=file is None)
    st.checkbox("Raspberry Pi", key="arm64_build", disabled=file is None)


if st.button("Build image", disabled=st.session_state.id is None or len(st.session_state.id) < 5 or file is None):
    with st.status("Building image...", expanded=True) as status:
        # Unzip the file to /tmp/<id>-<project>
        projectName = f"{textinput_cleaner(st.session_state.id)}-{textinput_cleaner(st.session_state.project_name)}"
        imageName = f"{REGISTRYNAME}/{textinput_cleaner(st.session_state.id)}/{textinput_cleaner(st.session_state.project_name)}".lower()
        projectPath = f"/tmp/{projectName}"
        imageTags : list = st.session_state.version_tag.split(",")

        # Clean tags
        imageTags = [textinput_cleaner(tag) for tag in imageTags]

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
            build = subprocess.run(f"docker buildx build --platform {build_targets} -t {imageName} {projectPath}", shell=True, universal_newlines=True, capture_output=True)
            history = subprocess.run(f"docker image history {imageName}", shell=True, universal_newlines=True, capture_output=True)

        if build.returncode != 0:
            st.error("Image build failed")
            st.text_area("Build Log", value=build.stderr, disabled=True)
            status.update(label="Failed to build image", state="error")
            st.stop()
        else:
            st.success("Image built")
            # Why does it output to stderr? Spent more time than needed trying to understand what was going on
            st.text_area("Build Log", value=build.stderr, disabled=True)
            # And then history to stdout... Make it make sense
            st.text_area("Image History", value=history.stdout, disabled=True)

        # Tag the image
        with st.spinner("Image tagging..."):
            st.write(imageTags)

        # Push the image
        with st.spinner("Pushing image..."):
            push = subprocess.run(f"docker push {imageName}", shell=True, universal_newlines=True, capture_output=True)

        if push.returncode != 0:
            st.error("Image push failed")
            st.text_area("Push Log", value=push.stderr, disabled=True)
            status.update(label="Failed to push image", state="error")
            st.stop()
        else:
            st.success("Image pushed")
            st.text_area("Push Log", value=push.stdout, disabled=True)

        # Clean up
        with st.spinner("Cleaning up..."):
            os.system(f"rm -rf {projectPath}")
        st.success("Cleaned up build artifacts")