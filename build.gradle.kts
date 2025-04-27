import Com_hayden_docker_gradle.DockerContext;

plugins {
    id("com.hayden.docker")
}

wrapDocker {
    ctx = arrayOf(
        DockerContext(
            "localhost:5001/cdc-agents",
            "${project.projectDir}/docker",
            "cdcAgents"
        )
    )
}

val enableDocker = project.property("enable-docker")?.toString()?.toBoolean()?.or(false) ?: false
val buildCdcAgents = project.property("build-cdc-agents")?.toString()?.toBoolean()?.or(false) ?: false

println("enableDocker: $enableDocker, buildCdcAgents: $buildCdcAgents")

if (enableDocker && buildCdcAgents) {

    afterEvaluate {

        tasks.getByPath("jar").finalizedBy("buildDocker")
        tasks.getByPath("jar").dependsOn("copyLibs")

        tasks.getByPath("jar").doLast {
            tasks.getByPath("cdcAgentsDockerImage").dependsOn("copyLibs")
            tasks.getByPath("pushImages").dependsOn("copyLibs")
        }

        tasks.register("buildDocker") {
            dependsOn("copyLibs", "bootJar", "cdcAgentsDockerImage", "pushImages")
        }

        tasks.register("copyLibs") {
            println("Copying libs.")
            exec {
                workingDir(projectDir.resolve("docker"))
                commandLine("./build.sh")
            }
        }

        tasks.getByPath("pushImages").doLast {
            println("Pushing model server docker image.")
            exec {
                workingDir(projectDir.resolve("docker"))
                commandLine("./after-build.sh")
            }
        }

    }
}

dependencies {
    project(":runner_code")
}
